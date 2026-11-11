// Integration check of the real client + page logic against a running API (devserver or Django).
// Usage: node --experimental-strip-types scripts/e2e-flow.ts http://127.0.0.1:8000/api/v1
import { createClient } from "../src/lib/api/client.ts";
import { decidePlanView } from "../src/lib/plan-view.ts";
import { buildProfileRequest, mealView } from "../src/lib/nutrition.ts";
import { SCREENING_QUESTIONS, SCREENING_VERSION } from "../src/lib/onboarding.ts";

const base = process.argv[2] ?? "http://127.0.0.1:8000/api/v1";
const jar = new Map<string, string>();
const fetchImpl = (async (url: string, init: RequestInit) => {
  const headers = { ...(init.headers as Record<string, string>), Cookie: [...jar].map(([k, v]) => `${k}=${v}`).join("; ") };
  const res = await fetch(url, { ...init, headers });
  for (const sc of res.headers.getSetCookie()) {
    const [kv] = sc.split(";"); const i = kv.indexOf("=");
    const k = kv.slice(0, i), v = kv.slice(i + 1);
    if (/Max-Age=0/i.test(sc)) jar.delete(k); else jar.set(k, v);
  }
  return res;
}) as unknown as typeof fetch;
const api = createClient({ baseUrl: base, fetchImpl, readCookie: (n) => jar.get(n) });

function ok<T>(label: string, r: { ok: boolean; status: number; data?: T; error?: unknown }): T {
  if (!r.ok) throw new Error(`${label}: HTTP ${r.status} ${JSON.stringify((r as { error: unknown }).error)}`);
  console.log(`ok  ${label} (${r.status})`);
  return r.data as T;
}

const email = `e2e${Date.now()}@example.com`;
const pw = "Abcdefghij1";
ok("register", await api.call("API-AUTH-001", { body: { email, password: pw, date_of_birth: "1990-01-01", language: "fa" } }));
async function verifyViaCapture(addr: string) {       // dev capture adapter only: the message was captured, NOT e-mailed
  const r = await fetch(`${base}/dev/captured-mail?kind=verification&to=${encodeURIComponent(addr)}`);
  if (!r.ok) throw new Error(`no captured verification message (HTTP ${r.status}); start the server with MAIL_PROVIDER=capture in debug`);
  const { secret } = (await r.json()) as { secret: string };
  ok("verify", await api.call("API-AUTH-002", { body: { identifier: addr, code: secret } }));
}
const unverified = await api.call("API-AUTH-003", { body: { identifier: email, password: pw } });
if (unverified.ok) throw new Error("login succeeded before e-mail verification");
console.log("ok  login refused before verification");
await verifyViaCapture(email);
const login = await api.call("API-AUTH-003", { body: { identifier: email, password: pw } });
if (!login.ok) { console.log("login failed (account may need email verification):", login.status, login.error.code); process.exit(2); }
console.log("ok  login ->", login.data.onboarding_status);
ok("profile (session works via cookie)", await api.call("API-PRO-001"));
const steps: Array<[string, Record<string, unknown>]> = [["1", { age: 30 }], ["2", { goal: "strength", level: "beginner" }], ["3", { days_per_week: 3, session_minutes: 60 }], ["4", { equipment: ["dumbbell"] }]];
for (const [s, a] of steps) ok(`onboarding step ${s}`, await api.call("API-ONB-002", { path: { step: s }, body: { answers: a } }));
const docs = ok("consent docs", await api.call("API-PRIV-001"));
const doc = docs.find((d) => d.type === "health_data")!;
ok("grant consent", await api.call("API-PRIV-002", { body: { document_id: doc.id!, granted: true } }));
const dec = ok("screening", await api.call("API-HEALTH-006", { body: { screening_version: SCREENING_VERSION, answers: Object.fromEntries(SCREENING_QUESTIONS.map((q) => [q, false])) } }));
console.log("    screening decision:", dec.status);
ok("complete onboarding", await api.call("API-ONB-003"));
const gen = ok("generate plan", await api.call("API-WO-001", { body: {} }));
const view = decidePlanView(gen.decision, gen.plan);
console.log("    plan view:", view.kind, gen.decision.status, "content_status:", (gen.plan as { rationale?: { content_status?: string } })?.rationale?.content_status);
const cur = await api.call("API-WO-002");
console.log("    current plan:", cur.ok ? "present" : `HTTP ${cur.status}`);

// nutrition: estimate, then a meal plan that must be NEEDS_CONTENT because no verified food/recipe content exists
const sc = { eating_disorder_risk: false, medical_diet_needed: false, pregnant_or_lactating: false };
const est = ok("nutrition profile", await api.call("API-NUT-001", { body: buildProfileRequest({ height_cm: 175, weight_kg: 70, activity: "moderate", screening: sc }) }));
console.log("    estimate:", est.status, est.tdee);
ok("nutrition estimate GET", await api.call("API-NUT-002"));
const mp = ok("meal plan", await api.call("API-NUT-003", { body: { days: 7 } }));
const mv = mealView(mp);
console.log("    meal view:", mv.kind, mp.status);
if (mv.kind === "plan") throw new Error("meal plan shown without verified content");
const est2 = ok("nutrition profile (REFER)", await api.call("API-NUT-001", { body: buildProfileRequest({ height_cm: 175, weight_kg: 70, activity: "moderate", screening: { ...sc, medical_diet_needed: true } }) }));
const mp2 = ok("meal plan after REFER", await api.call("API-NUT-003", { body: {} }));
console.log("    after refer:", est2.status, mealView(mp2).kind);
if (mealView(mp2).kind === "plan") throw new Error("meal plan shown for a referred user");

// negative path: a positive red flag must never yield a plan
const email2 = `e2e2${Date.now()}@example.com`;
await api.call("API-AUTH-001", { body: { email: email2, password: pw, date_of_birth: "1990-01-01" } });
await verifyViaCapture(email2);
ok("login #2", await api.call("API-AUTH-003", { body: { identifier: email2, password: pw } }));
for (const [s, a] of steps) ok(`#2 step ${s}`, await api.call("API-ONB-002", { path: { step: s }, body: { answers: a } }));
const d2 = (await api.call("API-PRIV-001")) as { ok: true; data: Array<{ id?: string; type?: string }> };
ok("#2 consent", await api.call("API-PRIV-002", { body: { document_id: d2.data.find((d) => d.type === "health_data")!.id!, granted: true } }));
const bad = ok("#2 screening chest_pain=yes", await api.call("API-HEALTH-006", { body: { screening_version: 1, answers: { chest_pain: true, fainting: false, severe_unexplained_pain: false, neurological_symptoms: false } } }));
ok("#2 complete onboarding", await api.call("API-ONB-003"));
const g2 = ok("#2 generate", await api.call("API-WO-001", { body: {} }));
const v2 = decidePlanView(g2.decision, g2.plan);
console.log("    decision:", bad.status, "->", g2.decision.status, "view:", v2.kind);
if (v2.kind === "plan") throw new Error("SAFETY VIOLATION: plan shown despite red flag");
ok("logout", await api.call("API-AUTH-004"));
const after = await api.call("API-PRO-001");
if (after.ok) throw new Error("session still valid after logout");
console.log("ok  session rejected after logout (" + after.status + ")");
console.log("E2E FLOW PASSED");

// Integration check of the real client + page logic against a running API (devserver or Django).
// Usage: node --experimental-strip-types scripts/e2e-flow.ts http://127.0.0.1:8000/api/v1
import { createClient } from "../src/lib/api/client.ts";
import { decidePlanView } from "../src/lib/plan-view.ts";
import { buildProfileRequest, mealView } from "../src/lib/nutrition.ts";
import { alertKind, buildMealRequest, toggleChecked, validatePrice } from "../src/lib/nutrition-log.ts";
import { buildSetLog, finishRequest, newUuid, plannedSets } from "../src/lib/workout-log.ts";
import { libraryQuery, NO_FILTERS } from "../src/lib/exercises.ts";
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
if (unverified.ok) throw new Error("login succeeded before verification");
console.log("ok  login refused before verification");
// Telegram verification (PRIMARY channel). MOCKED: the dev-only simulate route plays Telegram; the single-use token is real.
const wrong = await api.call("API-AUTH-010", { body: { identifier: email, password: "Wrong-Password-9" } });
if (wrong.ok || wrong.status !== 401) throw new Error("telegram link must require the password (generic 401)");
const link = ok("telegram link", await api.call("API-AUTH-010", { body: { identifier: email, password: pw } }));
const tgToken = new URL(link.deep_link).searchParams.get("start")!;
async function simulateStart(id: number, token: string) {
  const r = await fetch(`${base}/dev/telegram/simulate-start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ telegram_id: id, token }) });
  if (!r.ok) throw new Error(`simulate-start HTTP ${r.status}; start the server with TELEGRAM_PROVIDER=capture in debug (devserver does this)`);
}
await simulateStart(900001, "z".repeat(32));
if ((await api.call("API-AUTH-003", { body: { identifier: email, password: pw } })).ok) throw new Error("invalid token verified the account");
console.log("ok  invalid token did not verify");
await simulateStart(900001, tgToken);
console.log("ok  telegram verification (mocked bot)");
const replay = await api.call("API-AUTH-010", { body: { identifier: email, password: pw } });
if (replay.ok || replay.status !== 409) throw new Error("verified account should answer 409 on a new link request");
const login = await api.call("API-AUTH-003", { body: { identifier: email, password: pw } });
if (!login.ok) { console.log("login failed (account may need email verification):", login.status, login.error.code); process.exit(2); }
console.log("ok  login ->", login.data.onboarding_status);
ok("profile (session works via cookie)", await api.call("API-PRO-001"));
const tgs = ok("telegram status", await api.call("API-TG-002"));
if (!tgs.linked || tgs.notifications) throw new Error("telegram status must be linked with notifications OFF by default");
if (!ok("telegram notifications on", await api.call("API-TG-003", { body: { enabled: true } })).notifications) throw new Error("opt-in not recorded");
if (ok("telegram notifications off", await api.call("API-TG-003", { body: { enabled: false } })).notifications) throw new Error("opt-out not recorded");
ok("body: weight", await api.call("API-BODY-002", { body: { metric: "weight", value: 72.5, unit: "kg", source: "measured" } }));
ok("body: height", await api.call("API-BODY-002", { body: { metric: "height", value: 175, unit: "cm", source: "measured" } }));
const body = ok("body overview", await api.call("API-BODY-001"));
if (body.bmi?.value !== 23.7 || body.bmi.label !== "screening_index") throw new Error("BMI must be a labelled screening index (23.7)");
const badBody = await api.call("API-BODY-002", { body: { metric: "weight", value: 5, unit: "kg", source: "measured" } });
if (badBody.ok) throw new Error("an out-of-range measurement must be rejected");
const sess = ok("sessions list", await api.call("API-AUTH-007"));
if (!sess.some((x) => x.current)) throw new Error("the current session must be listed and marked current");
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

// exercise library + workout logging through the real client
const lib = ok("exercise library", await api.call("API-EX-001", { query: libraryQuery(NO_FILTERS, 1) }));
console.log("    library:", lib.count, "exercises");
if ((lib.results ?? []).length) {
  const f = ok("library filter", await api.call("API-EX-001", { query: libraryQuery({ q: "", muscle: lib.results![0].muscles![0], equipment: "", difficulty: "" }, 1) }));
  if (!(f.results ?? []).some((r) => r.id === lib.results![0].id)) throw new Error("muscle filter lost the exercise it was built from");
}
if (cur.ok && cur.data.days?.length) {
  const day = cur.data.days[0];
  const sets = plannedSets(day);
  const sess = ok("start session", await api.call("API-LOG-001", { body: { day_id: day.day_id! } }));
  const b = buildSetLog(sets[0], { reps: String(sets[0].repsMin ?? 8), load: "20", rpe: "7" }, newUuid());
  if (!b.ok) throw new Error("set log did not validate");
  const l1 = ok("log set", await api.call("API-LOG-002", { path: { session_id: sess.id! }, body: b.body }));
  const l2 = ok("log set retry (idempotent)", await api.call("API-LOG-002", { path: { session_id: sess.id! }, body: b.body }));
  if (l1.id !== l2.id) throw new Error("retry created a second log entry");
  const mid = ok("history in progress", await api.call("API-LOG-004")).find((x) => x.id === sess.id);
  if (mid?.status !== "in_progress" || mid.logged_sets?.length !== 1) throw new Error("session did not show the logged set");
  const fin = ok("finish (pain)", await api.call("API-LOG-003", { path: { session_id: sess.id! }, body: finishRequest({ difficulty: "6", stoppedForPain: true }) }));
  console.log("    finished: sets", fin.sets_done, "volume", fin.volume_kg);
  const after = ok("history after", await api.call("API-LOG-004")).find((x) => x.id === sess.id);
  if (after?.status !== "aborted" || after.aborted_reason !== "pain") throw new Error("pain stop not recorded");
  const dup = await api.call("API-LOG-002", { path: { session_id: sess.id! }, body: { ...b.body, client_uuid: newUuid() } });
  if (dup.ok) throw new Error("a set was accepted after the session finished");
  const dash = ok("dashboard", await api.call("API-DASH-001"));
  console.log("    dashboard plan:", JSON.stringify(dash.current_plan));
}

// nutrition: estimate, then a meal plan that must be NEEDS_CONTENT because no verified food/recipe content exists
const sc = { eating_disorder_risk: false, medical_diet_needed: false, pregnant_or_lactating: false };
const est = ok("nutrition profile", await api.call("API-NUT-001", { body: buildProfileRequest({ height_cm: 175, weight_kg: 70, activity: "moderate", screening: sc }) }));
console.log("    estimate:", est.status, est.tdee);
ok("nutrition estimate GET", await api.call("API-NUT-002"));
const mp = ok("meal plan", await api.call("API-NUT-003", { body: { days: 7 } }));
const mv = mealView(mp);
console.log("    meal view:", mv.kind, mp.status);
if (mv.kind === "plan") throw new Error("meal plan shown without verified content");
// Batch B: progression, saved allergens, food browsing, meal/water log, prices, shopping state (real client against the real API)
const prog = ok("progression", await api.call("API-WO-005"));
console.log("    progression items:", prog.items.length, prog.items.slice(0, 1).map((i) => i.action).join(","));
const estA = ok("nutrition profile with allergens", await api.call("API-NUT-001", { body: buildProfileRequest({ height_cm: 175, weight_kg: 70, activity: "moderate", screening: sc, allergens: ["milk"], diet_required: ["vegetarian"] }) }));
if (!(estA.allergens ?? []).includes("milk")) throw new Error("saved allergen not returned");
const foods = ok("foods browse", await api.call("API-FOOD-001", { query: { page_size: 50, avoid_allergens: "milk" } }));
if ((foods.results ?? []).some((f) => f.allergens.includes("milk"))) throw new Error("allergen filter returned a milk item");
console.log("    foods:", foods.count, "recipes:", ok("recipes browse", await api.call("API-REC-001", { query: {} })).count);
const f0 = (foods.results ?? [])[0];
if (f0) ok("food detail", await api.call("API-FOOD-002", { path: { food_id: f0.id } }));
const req = f0 ? buildMealRequest("lunch", { kind: "food", id: f0.id, grams: "150" }) : buildMealRequest("lunch", { kind: "manual", name: "Manual test", kcal: "300", protein_g: "", carbs_g: "", fat_g: "" });
const meal = ok("log meal", await api.call("API-NUT-004", { body: req! }));
console.log("    meal source:", meal.source, "alert:", alertKind(meal));
const bad0 = await api.call("API-NUT-004", { body: { slot: "lunch", food_id: "x", grams: 1, recipe_id: "y", servings: 1 } });
if (bad0.ok) throw new Error("meal with two sources was accepted");
ok("water", await api.call("API-NUT-007", { body: { ml: 250 } }));
const day = ok("meals today", await api.call("API-NUT-005", { query: {} }));
if (!day.meals.some((x) => x.id === meal.id)) throw new Error("logged meal missing from the day");
const sum = ok("summary", await api.call("API-NUT-008", { query: {} }));
if (sum.water_ml !== 250 || sum.meals < 1) throw new Error("summary does not reflect the log");
const future = await api.call("API-NUT-005", { query: { date: "2999-01-01" } });
if (future.ok) throw new Error("future date accepted");
if (f0) {
  const pr = validatePrice({ food_id: f0.id, price: "100", currency: "USD", region: "US" })!;
  ok("price set", await api.call("API-NUT-010", { body: pr }));
  if (!ok("prices", await api.call("API-NUT-009")).prices.some((p) => p.food_id === f0.id)) throw new Error("price not stored");
  ok("price delete", await api.call("API-NUT-011", { path: { food_id: f0.id } }));
}
const st = ok("shopping state set", await api.call("API-NUT-013", { body: { checked: toggleChecked([], "item-1") } }));
if (ok("shopping state get", await api.call("API-NUT-012")).checked.join() !== st.checked.join()) throw new Error("shopping state not persisted");
ok("delete meal", await api.call("API-NUT-006", { path: { meal_id: meal.id } }));
if (ok("meals after delete", await api.call("API-NUT-005", { query: {} })).meals.some((x) => x.id === meal.id)) throw new Error("meal not deleted");

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

"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { ConsentDocumentList, DataRequest, Profile, SessionList, ProfileUpdate, TelegramStatus } from "../../../lib/api/generated.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Field, Loading } from "../../../components/ui.tsx";
import { Select } from "../../../components/Select.tsx";
import { POLL_MS, clock, safeDeepLink, secondsLeft } from "../../../lib/telegram.ts";

type Doc = NonNullable<ConsentDocumentList[number]>;

function device(ua: string | undefined, fallback: string): string {
  const u = ua ?? "";
  const br = /Edg\//.test(u) ? "Edge" : /OPR\//.test(u) ? "Opera" : /Chrome\//.test(u) ? "Chrome" : /Firefox\//.test(u) ? "Firefox" : /Safari\//.test(u) ? "Safari" : "";
  const os = /Windows/.test(u) ? "Windows" : /Android/.test(u) ? "Android" : /iPhone|iPad|iOS/.test(u) ? "iOS" : /Mac OS/.test(u) ? "macOS" : /Linux/.test(u) ? "Linux" : "";
  return [br, os].filter(Boolean).join(" · ") || fallback;
}

/** Connect Telegram for a logged-in account: one button, then a guided wait that detects completion by itself. */
function TelegramCard({ tg, setTg }: { tg: TelegramStatus | null; setTg: (s: TelegramStatus) => void }) {
  const { t } = useT();
  const api = useApi();
  const [phase, setPhase] = useState<"idle" | "requesting" | "pending" | "expired" | "unavailable" | "error">("idle");
  const [msg, setMsg] = useState("");
  const [link, setLink] = useState<string | null>(null);
  const [expires, setExpires] = useState("");
  const [left, setLeft] = useState(0);
  const [justLinked, setJustLinked] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [offBusy, setOffBusy] = useState(false);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  const request = useCallback(async () => {
    setPhase("requesting"); setMsg("");
    const r = await api.call("API-TG-004");
    if (!alive.current) return;
    if (!r.ok) {
      if (r.status === 409) { const s = await api.call("API-TG-002"); if (s.ok) setTg(s.data); return setPhase("idle"); }
      if (r.status === 503) return setPhase("unavailable");
      setMsg(r.status === 429 ? "telegram.rateLimited" : "telegram.linkFailed"); return setPhase("error");
    }
    const url = safeDeepLink(r.data.deep_link);
    if (!url) { setMsg("telegram.linkFailed"); return setPhase("error"); }
    setLink(url); setExpires(r.data.expires_at); setLeft(secondsLeft(r.data.expires_at, Date.now())); setPhase("pending");
  }, [api, setTg]);

  useEffect(() => {
    if (phase !== "pending") return;
    const tick = setInterval(() => { const s = secondsLeft(expires, Date.now()); setLeft(s); if (s <= 0) setPhase("expired"); }, 1000);
    let stop = false; let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      if (stop) return;
      const r = await api.call("API-TG-002");
      if (stop || !alive.current) return;
      if (r.ok && r.data.linked) { setTg(r.data); setJustLinked(true); setPhase("idle"); return; }
      timer = setTimeout(poll, POLL_MS / 2);
    };
    timer = setTimeout(poll, 2000);
    return () => { stop = true; clearInterval(tick); clearTimeout(timer); };
  }, [phase, expires, api, setTg]);

  async function disconnect() {
    setOffBusy(true);
    const r = await api.call("API-TG-005");
    setOffBusy(false);
    if (!alive.current) return;
    if (r.ok) { setTg(r.data); setConfirming(false); setJustLinked(false); setPhase("idle"); }
    else { setMsg("telegram.linkFailed"); setPhase("error"); setConfirming(false); }
  }

  if (tg?.linked) {
    return (
      <>
      <div className={`tg-ok ${justLinked ? "fresh" : ""}`}>
        <span className="tg-badge" aria-hidden="true"><svg viewBox="0 0 24 24" width="26" height="26"><path d="M20 4 3 11l5 2 2 6 3-4 5 4z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg></span>
        <div><strong>{justLinked ? t("tg.done") : t("tg.connected.title")}</strong><p className="hint">{t("telegram.settings.linked")}</p></div>
        {!confirming && <button type="button" className="btn btn-secondary tg-off" onClick={() => setConfirming(true)}>{t("tg.disconnect")}</button>}
      </div>
      {confirming && (
        <div className="tg-confirm" role="alertdialog" aria-labelledby="tgc-t">
          <strong id="tgc-t">{t("tg.disconnect.title")}</strong>
          <p>{t("tg.disconnect.body")}</p>
          <div className="row">
            <Button type="button" busy={offBusy} onClick={disconnect}>{t("tg.disconnect.yes")}</Button>
            <button type="button" className="btn btn-secondary" onClick={() => setConfirming(false)}>{t("sub.cancel")}</button>
          </div>
        </div>
      )}
      </>
    );
  }
  return (
    <div className="tg">
      <ol className="tg-steps" aria-label={t("telegram.settings.title")}>
        {[1, 2, 3].map((k) => (<li key={k} className={phase === "pending" && k === 2 ? "now" : phase === "pending" && k === 1 ? "done" : k === 1 && phase === "idle" ? "now" : ""}><i aria-hidden="true">{k}</i><span>{t(`tg.step.${k}`)}</span></li>))}
      </ol>
      {phase === "unavailable" && <Alert kind="warning">{t("telegram.unavailable")}</Alert>}
      {phase === "error" && <Alert kind="error">{t(msg)}</Alert>}
      {phase === "expired" && <Alert kind="warning">{t("telegram.expired")}</Alert>}
      {phase === "pending" && link ? (
        <div className="tg-wait" aria-live="polite">
          <a className="btn cta" href={link} target="_blank" rel="noopener noreferrer">{t("telegram.open")}</a>
          <p className="muted"><span className="tg-dot" aria-hidden="true" /> {t("tg.waiting")} <bdi dir="ltr">{clock(left)}</bdi></p>
        </div>
      ) : (
        <Button type="button" busy={phase === "requesting"} onClick={request}>{phase === "expired" || phase === "error" ? t("tg.retry") : t("tg.connect")}</Button>
      )}
      <div className="tg-why">
        <strong>{t("tg.why.title")}</strong>
        <ul>{[1, 2, 3].map((k) => <li key={k}>{t(`tg.why.${k}`)}</li>)}</ul>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const [p, setP] = useState<Profile | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [state, setState] = useState<Record<string, boolean>>({});
  const [tg, setTg] = useState<TelegramStatus | null>(null);
  const [sessions, setSessions] = useState<SessionList>([]);
  const [exp, setExp] = useState<DataRequest | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pw, setPw] = useState(""); const [sure, setSure] = useState(false); const [deleting, setDeleting] = useState(false);

  const fail = (e: ApiError, s: number) => { if (s === 401) router.replace(`/${locale}/login`); else setError(e); };

  useEffect(() => {
    let live = true;
    Promise.all([api.call("API-PRO-001"), api.call("API-PRIV-001"), api.call("API-TG-002"), api.call("API-AUTH-007")]).then(([a, b, g, ss]) => {
      if (!live) return;
      if (!a.ok) return fail(a.error, a.status);
      setP(a.data); if (b.ok) setDocs(b.data as Doc[]);
      if (g.ok) setTg(g.data);
      if (ss.ok) setSessions(ss.data);
    });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  async function endSession(id: string) {
    setError(null);
    const r = await api.call("API-AUTH-008", { path: { session_id: id } });
    if (!r.ok) return fail(r.error, r.status);
    setSessions((list) => list.filter((x) => x.id !== id));
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!p) return;
    const body: ProfileUpdate = { display_name: p.display_name, sex: p.sex, country: p.country, language: p.language, calendar: p.calendar, unit_system: p.unit_system, digit_style: p.digit_style };
    Object.keys(body).forEach((k) => (body as Record<string, unknown>)[k] === undefined && delete (body as Record<string, unknown>)[k]);
    setBusy(true); setError(null); setSaved(false);
    const r = await api.call("API-PRO-002", { body });
    setBusy(false);
    if (!r.ok) return fail(r.error, r.status);
    setP(r.data); setSaved(true);
  }
  async function consent(d: Doc, granted: boolean) {
    if (!d.id) return;
    const r = await api.call("API-PRIV-002", { body: { document_id: d.id, granted } });
    if (!r.ok) return fail(r.error, r.status);
    setState({ ...state, [d.id]: r.data.granted === true });
  }
  async function notifications(enabled: boolean) {
    setError(null);
    const r = await api.call("API-TG-003", { body: { enabled } });
    if (!r.ok) return fail(r.error, r.status);
    setTg(r.data);
  }
  async function requestExport() {
    setBusy(true); const r = await api.call("API-PRIV-003"); setBusy(false);
    if (!r.ok) return fail(r.error, r.status);
    setExp(r.data);
    if (r.data.id) { const s = await api.call("API-PRIV-005", { path: { request_id: r.data.id } }); if (s.ok) setExp(s.data); }
  }
  async function download() {
    if (!exp?.id) return;
    const r = await api.call("API-PRIV-006", { path: { request_id: exp.id } });
    if (!r.ok) return r.status === 410 ? setExp({ ...exp, status: "failed" }) : fail(r.error, r.status);
    const url = URL.createObjectURL(new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" }));
    const a = document.createElement("a"); a.href = url; a.download = "vitaforge-export.json"; a.click();
    URL.revokeObjectURL(url);
  }
  async function del(e: FormEvent) {
    e.preventDefault();
    if (!sure || !pw) return;
    setDeleting(true); setError(null);
    const r = await api.call("API-PRIV-004", { body: { password: pw, confirm: true } });
    setDeleting(false);
    if (!r.ok) return fail(r.error, r.status);
    router.replace(`/${locale}`);
  }

  if (!p) return <Card title={t("profile.title")}>{error ? <ApiErrorView error={error} /> : <Loading />}</Card>;
  const set = <K extends keyof Profile>(k: K, v: Profile[K]) => { setSaved(false); setP({ ...p, [k]: v }); };
  const initials = (p.display_name ?? "").trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase() || "V";
  const sec = [["account", "pf.nav.account"], ["telegram", "pf.nav.telegram"], ["privacy", "pf.nav.privacy"], ["sessions", "pf.nav.sessions"], ["data", "pf.nav.data"]] as const;
  return (
    <div className="pf">
      <header className="pf-hero card">
        <span className="pf-avatar" aria-hidden="true"><b>{initials}</b></span>
        <div>
          <h1>{p.display_name || t("profile.title")}</h1>
          <p className="muted">{t("pf.hero.hint")}</p>
          <p className="pf-chips"><span>{t(`language.${p.language ?? "fa"}`)}</span><span>{t(`profile.units.${p.unit_system ?? "metric"}`)}</span><span className={tg?.linked ? "ok" : "off"}>{tg?.linked ? t("tg.connected.title") : t("telegram.settings.notLinked")}</span></p>
        </div>
      </header>
      <ApiErrorView error={error} />
      <nav className="pf-nav" aria-label={t("profile.title")}>{sec.map(([id, k]) => <a key={id} href={`#${id}`}>{t(k)}</a>)}</nav>

      <section className="card pf-sec" id="account">
        <h2>{t("pf.account.title")}</h2>
        <form onSubmit={save} noValidate className="formgrid">
          <Field id="dn" label={t("profile.displayName")}><input id="dn" maxLength={60} value={p.display_name ?? ""} onChange={(e) => set("display_name", e.target.value)} /></Field>
          <Field id="pl" label={t("profile.language")}><Select id="pl" value={p.language ?? "fa"} onChange={(e) => set("language", e.target.value as Profile["language"])}><option value="fa">{t("language.fa")}</option><option value="en">{t("language.en")}</option></Select></Field>
          <Field id="pu" label={t("profile.units")}><Select id="pu" value={p.unit_system ?? "metric"} onChange={(e) => set("unit_system", e.target.value as Profile["unit_system"])}><option value="metric">{t("profile.units.metric")}</option><option value="imperial">{t("profile.units.imperial")}</option></Select></Field>
          <Field id="pc" label={t("profile.calendar")}><Select id="pc" value={p.calendar ?? "jalali"} onChange={(e) => set("calendar", e.target.value as Profile["calendar"])}><option value="jalali">{t("profile.calendar.jalali")}</option><option value="gregorian">{t("profile.calendar.gregorian")}</option></Select></Field>
          <Field id="pd" label={t("profile.digits")}><Select id="pd" value={p.digit_style ?? "persian"} onChange={(e) => set("digit_style", e.target.value as Profile["digit_style"])}><option value="persian">{t("profile.digits.persian")}</option><option value="latin">{t("profile.digits.latin")}</option></Select></Field>
          <Field id="ps" label={t("nut.sex")}><Select id="ps" value={p.sex ?? "unspecified"} onChange={(e) => set("sex", e.target.value as Profile["sex"])}><option value="unspecified">{t("sex.unset")}</option><option value="male">{t("sex.male")}</option><option value="female">{t("sex.female")}</option></Select></Field>
          <Button type="submit" busy={busy}>{t("profile.save")}</Button>
          {saved && <Alert kind="success">{t("profile.saved")}</Alert>}
        </form>
      </section>

      <section className="card pf-sec" id="telegram">
        <h2>{t("telegram.settings.title")}</h2>
        <TelegramCard tg={tg} setTg={setTg} />
        {tg?.linked && (
          <div className="pf-switch">
            <div><strong>{t("tg.notify.title")}</strong><p className="hint">{t("telegram.settings.notifyHint")}</p></div>
            <label className="switch"><input type="checkbox" role="switch" checked={tg.notifications} onChange={(e) => notifications(e.target.checked)} aria-label={t("telegram.settings.notify")} /><i aria-hidden="true" /></label>
          </div>
        )}
      </section>

      <section className="card pf-sec" id="privacy">
        <h2>{t("profile.consents")}</h2>
        <p className="hint">{t("profile.consents.hint")}</p>
        {docs.length === 0 && <p className="muted">{t("consent.noDoc")}</p>}
        <ul className="plain pf-list">
          {docs.map((d) => (
            <li key={d.id}>
              <div><strong>{d.type}</strong> <span className="muted">{t("consent.docVersion", { n: d.version ?? 0 })}</span>
                {d.id && state[d.id] !== undefined && <span className={state[d.id] ? "pf-tag ok" : "pf-tag"}>{state[d.id] ? t("profile.consent.granted") : t("profile.consent.withdrawn")}</span>}</div>
              <div className="row"><Button type="button" onClick={() => consent(d, true)}>{t("profile.consent.grant")}</Button>{d.type !== "terms" && <Button type="button" className="btn-secondary" onClick={() => consent(d, false)}>{t("profile.consent.withdraw")}</Button>}</div>
            </li>))}
        </ul>
      </section>

      <section className="card pf-sec" id="sessions">
        <h2>{t("profile.sessions.title")}</h2>
        <p className="hint">{t("profile.sessions.hint")}</p>
        <ul className="plain pf-list">
          {sessions.map((x) => (
            <li key={x.id}>
              <div><strong>{device(x.user_agent, t("pf.device.unknown"))}</strong>{x.current && <span className="pf-tag ok">{t("profile.sessions.current")}</span>}
                <p className="muted"><bdi dir="ltr">{x.last_seen_at ?? ""}</bdi></p></div>
              {!x.current && x.id && <div className="row"><Button type="button" className="btn-secondary" onClick={() => endSession(x.id!)}>{t("profile.sessions.end")}</Button></div>}
            </li>))}
        </ul>
      </section>

      <section className="card pf-sec" id="data">
        <h2>{t("profile.data")}</h2>
        <Button type="button" busy={busy} onClick={requestExport}>{t("profile.export")}</Button>
        {exp && <Alert kind="info">{t("profile.export.status", { status: t(`profile.status.${exp.status ?? "requested"}`) })}</Alert>}
        {exp?.status === "completed" && <><p className="hint">{t("profile.export.hint")}</p><Button type="button" onClick={download}>{t("profile.export.download")}</Button></>}
        {exp?.status === "failed" && <Alert kind="warning">{t("profile.export.expired")}</Alert>}
        <details className="pf-danger">
          <summary>{t("pf.danger")}</summary>
          <h3>{t("profile.delete.title")}</h3>
          <Alert kind="warning">{t("profile.delete.body")}</Alert>
          <form onSubmit={del} noValidate>
            <Field id="dpw" label={t("auth.password")}><input id="dpw" type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
            <label className="check"><input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} />{t("profile.delete.confirm")}</label>
            <Button type="submit" busy={deleting} disabled={!sure || !pw}>{t("profile.delete.submit")}</Button>
          </form>
        </details>
      </section>
    </div>
  );
}

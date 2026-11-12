"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { ConsentDocumentList, DataRequest, Profile, ProfileUpdate } from "../../../lib/api/generated.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Field, Loading } from "../../../components/ui.tsx";

type Doc = NonNullable<ConsentDocumentList[number]>;

export default function ProfilePage() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const [p, setP] = useState<Profile | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [state, setState] = useState<Record<string, boolean>>({});
  const [exp, setExp] = useState<DataRequest | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pw, setPw] = useState(""); const [sure, setSure] = useState(false); const [deleting, setDeleting] = useState(false);

  const fail = (e: ApiError, s: number) => { if (s === 401) router.replace(`/${locale}/login`); else setError(e); };

  useEffect(() => {
    let live = true;
    Promise.all([api.call("API-PRO-001"), api.call("API-PRIV-001")]).then(([a, b]) => {
      if (!live) return;
      if (!a.ok) return fail(a.error, a.status);
      setP(a.data); if (b.ok) setDocs(b.data as Doc[]);
    });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

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
  return (
    <>
      <Card title={t("profile.title")}>
        <ApiErrorView error={error} />
        <form onSubmit={save} noValidate>
          <Field id="dn" label={t("profile.displayName")}><input id="dn" maxLength={60} value={p.display_name ?? ""} onChange={(e) => set("display_name", e.target.value)} /></Field>
          <Field id="pl" label={t("profile.language")}><select id="pl" value={p.language ?? "fa"} onChange={(e) => set("language", e.target.value as Profile["language"])}><option value="fa">{t("language.fa")}</option><option value="en">{t("language.en")}</option></select></Field>
          <Field id="pu" label={t("profile.units")}><select id="pu" value={p.unit_system ?? "metric"} onChange={(e) => set("unit_system", e.target.value as Profile["unit_system"])}><option value="metric">{t("profile.units.metric")}</option><option value="imperial">{t("profile.units.imperial")}</option></select></Field>
          <Field id="pc" label={t("profile.calendar")}><select id="pc" value={p.calendar ?? "jalali"} onChange={(e) => set("calendar", e.target.value as Profile["calendar"])}><option value="jalali">{t("profile.calendar.jalali")}</option><option value="gregorian">{t("profile.calendar.gregorian")}</option></select></Field>
          <Field id="pd" label={t("profile.digits")}><select id="pd" value={p.digit_style ?? "persian"} onChange={(e) => set("digit_style", e.target.value as Profile["digit_style"])}><option value="persian">{t("profile.digits.persian")}</option><option value="latin">{t("profile.digits.latin")}</option></select></Field>
          <Field id="ps" label={t("nut.sex")}><select id="ps" value={p.sex ?? "unspecified"} onChange={(e) => set("sex", e.target.value as Profile["sex"])}><option value="unspecified">{t("sex.unset")}</option><option value="male">{t("sex.male")}</option><option value="female">{t("sex.female")}</option></select></Field>
          <Button type="submit" busy={busy}>{t("profile.save")}</Button>
          {saved && <Alert kind="success">{t("profile.saved")}</Alert>}
        </form>
      </Card>

      <Card title={t("profile.consents")}>
        <p className="hint">{t("profile.consents.hint")}</p>
        {docs.length === 0 && <p className="muted">{t("consent.noDoc")}</p>}
        <ul className="plain">
          {docs.map((d) => (
            <li key={d.id}>
              <strong>{d.type}</strong> <span className="muted">{t("consent.docVersion", { n: d.version ?? 0 })}</span>
              {d.id && state[d.id] !== undefined && <span> — {state[d.id] ? t("profile.consent.granted") : t("profile.consent.withdrawn")}</span>}
              <div className="row"><Button type="button" onClick={() => consent(d, true)}>{t("profile.consent.grant")}</Button>{d.type !== "terms" && <Button type="button" onClick={() => consent(d, false)}>{t("profile.consent.withdraw")}</Button>}</div>
            </li>))}
        </ul>
      </Card>

      <Card title={t("profile.data")}>
        <Button type="button" busy={busy} onClick={requestExport}>{t("profile.export")}</Button>
        {exp && <Alert kind="info">{t("profile.export.status", { status: t(`profile.status.${exp.status ?? "requested"}`) })}</Alert>}
        {exp?.status === "completed" && <><p className="hint">{t("profile.export.hint")}</p><Button type="button" onClick={download}>{t("profile.export.download")}</Button></>}
        {exp?.status === "failed" && <Alert kind="warning">{t("profile.export.expired")}</Alert>}
      </Card>

      <Card title={t("profile.delete.title")}>
        <Alert kind="warning">{t("profile.delete.body")}</Alert>
        <form onSubmit={del} noValidate>
          <Field id="dpw" label={t("auth.password")}><input id="dpw" type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} /></Field>
          <label className="check"><input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} />{t("profile.delete.confirm")}</label>
          <Button type="submit" busy={deleting} disabled={!sure || !pw}>{t("profile.delete.submit")}</Button>
        </form>
      </Card>
    </>
  );
}

"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { AssessmentResult } from "../../../lib/api/generated.ts";
import { buildAnswers, DOMAIN_ORDER, STEPS, type Draft, type FieldSpec, type Profile } from "../../../lib/assessment.ts";
import { PAIN_REGIONS } from "../../../lib/workout-log.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Field, Loading } from "../../../components/ui.tsx";

export default function AssessmentPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [res, setRes] = useState<AssessmentResult | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [editing, setEditing] = useState(false);
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState<Draft>({});
  const [pain, setPain] = useState<string[]>([]);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void api.call("API-ASSESS-001").then((r) => {
      if (r.ok) return setRes(r.data);
      if (r.status === 401) return router.replace(`/${locale}/login`);
      setError(r.error); setRes({});
    });
  }, [api, locale, router]);

  const set = (k: string, v: string) => setDraft((d) => ({ ...d, [k]: v }));
  const last = step === STEPS.length;               // final step = pain question + submit

  async function submit(e: FormEvent) {
    e.preventDefault();
    const b = buildAnswers(draft, pain);
    if (!b.ok) { setErrs(b.errors); if (b.errors._form) setStep(0); return; }
    setErrs({}); setBusy(true); setError(null);
    const r = await api.call("API-ASSESS-002", { body: { answers: b.answers } });
    setBusy(false);
    if (!r.ok) { if (r.status === 401) return router.replace(`/${locale}/login`); return setError(r.error); }
    setRes(r.data); setEditing(false);
  }

  function control(f: FieldSpec) {
    const v = draft[f.key] ?? "";
    const e = errs[f.key] ? t(`assess.err.${errs[f.key]}`) : undefined;
    const hint = t(`assess.h.${f.key}`);
    return (
      <Field key={f.key} id={f.key} label={t(`assess.f.${f.key}`)} hint={hint} error={e}>
        {f.kind === "int" ? (
          <input id={f.key} inputMode="numeric" dir="ltr" autoComplete="off" value={v} onChange={(x) => set(f.key, x.target.value)} placeholder={f.unit ? t(`assess.unit.${f.unit}`) : undefined} />
        ) : f.kind === "enum" ? (
          <select id={f.key} value={v} onChange={(x) => set(f.key, x.target.value)}>
            <option value="">{t("assess.skip")}</option>
            {f.options.map((o) => <option key={o} value={o}>{t(`assess.o.${f.key}.${o}`)}</option>)}
          </select>
        ) : (
          <select id={f.key} value={v} onChange={(x) => set(f.key, x.target.value)}>
            <option value="">{t("assess.skip")}</option><option value="yes">{t("assess.yes")}</option><option value="no">{t("assess.no")}</option>
          </select>
        )}
      </Field>
    );
  }

  const profile = (res?.profile ?? null) as Profile | null;
  if (!res && !error) return <Loading />;

  if (profile && !editing) {
    return (
      <Card title={t("assess.resultTitle")}>
        <Alert kind="info">{t("assess.aiLabel")}</Alert>
        {profile.overall_level && <p>{t("assess.overall", { level: t(`assess.level.${profile.overall_level}`) })}</p>}
        <ul className="plain">
          {DOMAIN_ORDER.map((d) => {
            const x = profile.domains[d];
            return (
              <li key={d}>
                <strong>{t(`assess.domain.${d}`)}</strong>{" "}
                {x?.score == null ? <span className="muted">{t("assess.untested")}</span> : (
                  <>
                    <meter min={0} max={100} value={x.score} aria-label={t(`assess.domain.${d}`)} /> {n(x.score)}/{n(100)} — {t(`assess.band.${x.band}`)}
                  </>)}
              </li>);
          })}
        </ul>
        {profile.strengths.length > 0 && <p><strong>{t("assess.strengths")}:</strong> {profile.strengths.map((s) => t(`assess.domain.${s.domain}`)).join("، ")}</p>}
        {profile.weaknesses.length > 0 && <p><strong>{t("assess.weaknesses")}:</strong> {profile.weaknesses.map((s) => t(`assess.domain.${s.domain}`)).join("، ")}</p>}
        {profile.flags.length > 0 && (
          <ul className="plain">{profile.flags.map((f, i) => (
            <li key={i}>{t(`assess.flag.${f.key}`, { side: f.weaker_side ? t(`assess.side.${f.weaker_side}`) : "", gap: n(f.gap_pct ?? f.gap ?? 0), lagging: f.lagging ? t(`assess.domain.${f.lagging}`) : "" })}</li>))}
          </ul>)}
        {profile.limiters.length > 0 && (
          <><p><strong>{t("assess.limiters")}:</strong></p>
            <ul className="plain">{profile.limiters.map((k) => <li key={k}>{t(`assess.limiter.${k}`)}</li>)}</ul></>)}
        {profile.pain_reported && <Alert kind="warning">{t("assess.painNote")} <Link href={`/${locale}/health`}>{t("nav.health")}</Link></Alert>}
        <p className="muted">{t("assess.disclaimer")}</p>
        <Button type="button" onClick={() => { setEditing(true); setStep(0); setDraft({}); setPain([]); }}>{t("assess.retake")}</Button>
      </Card>
    );
  }

  return (
    <Card title={t("assess.title")}>
      <p className="hint">{t("assess.intro")}</p>
      <ApiErrorView error={error} />
      {errs._form && <Alert>{t("assess.err.empty")}</Alert>}
      <form onSubmit={submit} noValidate>
        <p className="muted" aria-live="polite">{t("assess.progress", { n: n(Math.min(step + 1, STEPS.length + 1)), total: n(STEPS.length + 1) })}</p>
        {!last ? (
          <fieldset><legend>{t(`assess.step.${STEPS[step].id}`)}</legend>{STEPS[step].fields.map(control)}</fieldset>
        ) : (
          <fieldset>
            <legend>{t("assess.painQuestion")}</legend>
            <p className="hint">{t("assess.painHint")}</p>
            {PAIN_REGIONS.map((r) => (
              <label key={r} className="check"><input type="checkbox" checked={pain.includes(r)} onChange={(x) => setPain((p) => x.target.checked ? [...p, r] : p.filter((y) => y !== r))} /> {t(`region.${r}`)}</label>))}
          </fieldset>)}
        <div className="row">
          {step > 0 && <Button type="button" onClick={() => setStep(step - 1)}>{t("assess.back")}</Button>}
          {!last ? <Button type="button" onClick={() => setStep(step + 1)}>{t("assess.next")}</Button> : <Button type="submit" busy={busy}>{t("assess.finish")}</Button>}
        </div>
      </form>
    </Card>
  );
}

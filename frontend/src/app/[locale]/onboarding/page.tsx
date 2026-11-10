"use client";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { ConsentDocumentList, SafetyDecision } from "../../../lib/api/generated.ts";
import { normalizeDigits } from "../../../lib/i18n.ts";
import {
  allScreeningAnswered, EQUIPMENT, GOALS, LEVELS, parseIntField, resumeStage, SCREENING_QUESTIONS, SCREENING_VERSION, STEP_NUMBER,
  validateBasics, validateEquipment, validateGoal, validateSchedule, type FieldErrors, type StepName, type WizardStage,
} from "../../../lib/onboarding.ts";
import { permitsPlan } from "../../../lib/plan-view.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field, Loading } from "../../../components/ui.tsx";
import { DecisionPanel } from "../../../components/DecisionPanel.tsx";

const STAGES: WizardStage[] = ["basics", "goal", "schedule", "equipment", "consent", "screening", "finish"];

function Wizard() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const forced = useSearchParams().get("stage") as WizardStage | null;

  const [stage, setStage] = useState<WizardStage | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [fieldErr, setFieldErr] = useState<FieldErrors>({});
  const [decision, setDecision] = useState<SafetyDecision | null>(null);

  const [age, setAge] = useState("");
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("");
  const [days, setDays] = useState("3");
  const [minutes, setMinutes] = useState("60");
  const [equipment, setEquipment] = useState<string[]>([]);
  const [docs, setDocs] = useState<ConsentDocumentList>([]);
  const [agree, setAgree] = useState(false);
  const [answers, setAnswers] = useState<Record<string, boolean | undefined>>({});

  // Resume from server state. Consent state is probed through a consent-gated read (no dedicated GET exists in the contract).
  useEffect(() => {
    let live = true;
    (async () => {
      const o = await api.call("API-ONB-001");
      if (!live) return;
      if (!o.ok) {
        if (o.status === 401) return router.replace(`/${locale}/login`);
        setError(o.error); setStage("basics"); return;
      }
      const a = (o.data.answers ?? {}) as Record<string, Record<string, unknown>>;
      if (a.basics?.age !== undefined) setAge(String(a.basics.age));
      if (typeof a.goal?.goal === "string") setGoal(a.goal.goal);
      if (typeof a.goal?.level === "string") setLevel(a.goal.level);
      if (a.schedule?.days_per_week !== undefined) setDays(String(a.schedule.days_per_week));
      if (a.schedule?.session_minutes !== undefined) setMinutes(String(a.schedule.session_minutes));
      if (Array.isArray(a.equipment?.equipment)) setEquipment(a.equipment.equipment as string[]);
      const probe = o.data.summary_ready ? await api.call("API-HEALTH-001") : null;
      if (!live) return;
      const next = resumeStage(o.data, !!probe && probe.ok);
      setStage(forced && STAGES.includes(forced) && STAGES.indexOf(forced) <= STAGES.indexOf(next === "finish" ? "finish" : next) ? forced : next);
    })();
    return () => { live = false; };
  }, [api, router, locale, forced]);

  useEffect(() => {
    if (stage !== "consent") return;
    api.call("API-PRIV-001").then((r) => { if (r.ok) setDocs(r.data); else setError(r.error); });
  }, [stage, api]);

  const saveStep = useCallback(async (name: StepName, body: Record<string, unknown>, errs: FieldErrors, next: WizardStage) => {
    setFieldErr(errs);
    if (Object.keys(errs).length) return;
    setBusy(true); setError(null);
    const r = await api.call("API-ONB-002", { path: { step: String(STEP_NUMBER[name]) }, body: { answers: body } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setStage(next);
  }, [api]);

  const progress = stage ? STAGES.indexOf(stage) + 1 : 1;
  const label = (s: WizardStage) => t(`onb.s.${s}`);
  const fe = (k: string) => (fieldErr[k] ? t("error.validation_failed") : undefined);

  async function submitConsent(e: FormEvent) {
    e.preventDefault();
    const doc = docs.find((d) => d.type === "health_data");
    if (!doc?.id || !agree) { setFieldErr({ agree: "agree" }); return; }
    setFieldErr({}); setBusy(true); setError(null);
    const r = await api.call("API-PRIV-002", { body: { document_id: doc.id, granted: true } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setStage("screening");
  }

  async function submitScreening(e: FormEvent) {
    e.preventDefault();
    if (!allScreeningAnswered(answers)) { setFieldErr({ screening: "all" }); return; }
    setFieldErr({}); setBusy(true); setError(null); setDecision(null);
    const r = await api.call("API-HEALTH-006", { body: { screening_version: SCREENING_VERSION, answers: answers as Record<string, boolean> } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    if (permitsPlan(r.data.status)) setStage("finish");
    else setDecision(r.data);               // NEEDS_INFO / STOP_AND_REFER / BLOCK_*: shown as-is, the wizard does not advance
  }

  async function complete() {
    setBusy(true); setError(null);
    const r = await api.call("API-ONB-003");
    setBusy(false);
    if (!r.ok) return setError(r.error);
    router.push(`/${locale}/plan`);
  }

  if (!stage) return <Card title={t("onb.title")}><Loading /><ApiErrorView error={error} /></Card>;
  const healthDoc = docs.find((d) => d.type === "health_data");

  return (
    <Card title={t("onb.title")}>
      <p className="muted" aria-live="polite">{t("common.step", { n: progress, total: STAGES.length })} · {label(stage)}</p>
      <progress value={progress} max={STAGES.length} aria-label={t("onb.title")} />
      <ApiErrorView error={error} />

      {stage === "basics" && (
        <form noValidate onSubmit={(e) => { e.preventDefault(); const v = parseIntField(normalizeDigits(age)); saveStep("basics", { age: v }, validateBasics({ age: v }), "goal"); }}>
          <Field id="age" label={t("onb.age")} error={fe("age")}><input id="age" inputMode="numeric" dir="ltr" value={age} onChange={(e) => setAge(e.target.value)} /></Field>
          <Button type="submit" busy={busy}>{t("common.next")}</Button>
        </form>
      )}

      {stage === "goal" && (
        <form noValidate onSubmit={(e) => { e.preventDefault(); saveStep("goal", { goal, level }, validateGoal({ goal, level }), "schedule"); }}>
          <Field id="goal" label={t("onb.goal")} error={fe("goal")}>
            <select id="goal" value={goal} onChange={(e) => setGoal(e.target.value)}><option value="" />{GOALS.map((g) => <option key={g} value={g}>{t(`goal.${g}`)}</option>)}</select>
          </Field>
          <Field id="level" label={t("onb.level")} error={fe("level")}>
            <select id="level" value={level} onChange={(e) => setLevel(e.target.value)}><option value="" />{LEVELS.map((g) => <option key={g} value={g}>{t(`level.${g}`)}</option>)}</select>
          </Field>
          <div className="row"><button type="button" className="btn-secondary" onClick={() => setStage("basics")}>{t("common.back")}</button><Button type="submit" busy={busy}>{t("common.next")}</Button></div>
        </form>
      )}

      {stage === "schedule" && (
        <form noValidate onSubmit={(e) => {
          e.preventDefault();
          const d = parseIntField(normalizeDigits(days)), m = parseIntField(normalizeDigits(minutes));
          saveStep("schedule", { days_per_week: d, session_minutes: m }, validateSchedule({ days_per_week: d, session_minutes: m }), "equipment");
        }}>
          <Field id="days" label={t("onb.days")} hint="1–6" error={fe("days_per_week")}><input id="days" inputMode="numeric" dir="ltr" value={days} onChange={(e) => setDays(e.target.value)} /></Field>
          <Field id="minutes" label={t("onb.minutes")} hint="20–180" error={fe("session_minutes")}><input id="minutes" inputMode="numeric" dir="ltr" value={minutes} onChange={(e) => setMinutes(e.target.value)} /></Field>
          <div className="row"><button type="button" className="btn-secondary" onClick={() => setStage("goal")}>{t("common.back")}</button><Button type="submit" busy={busy}>{t("common.next")}</Button></div>
        </form>
      )}

      {stage === "equipment" && (
        <form noValidate onSubmit={(e) => { e.preventDefault(); saveStep("equipment", { equipment }, validateEquipment({ equipment }), "consent"); }}>
          <fieldset><legend>{t("onb.equipment")}</legend><p className="hint">{t("onb.equipment.hint")}</p>
            <div className="checks">{EQUIPMENT.map((q) => (
              <label key={q} className="check"><input type="checkbox" checked={equipment.includes(q)} onChange={(e) => setEquipment(e.target.checked ? [...equipment, q] : equipment.filter((x) => x !== q))} />{t(`equip.${q}`)}</label>
            ))}</div>
          </fieldset>
          <div className="row"><button type="button" className="btn-secondary" onClick={() => setStage("schedule")}>{t("common.back")}</button><Button type="submit" busy={busy}>{t("common.next")}</Button></div>
        </form>
      )}

      {stage === "consent" && (
        <form noValidate onSubmit={submitConsent}>
          <h2>{t("consent.title")}</h2>
          {!healthDoc && <p className="muted">{error ? t("consent.noDoc") : t("common.loading")}</p>}
          {healthDoc && (<>
            {healthDoc.version === 0 && <Alert kind="warning">{t("consent.draftNotice")}</Alert>}
            <blockquote className="doc" lang={healthDoc.locale}>{healthDoc.body}</blockquote>
            <label className="check"><input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />{t("consent.accept")}</label>
            {fieldErr.agree && <p className="field-error" role="alert">{t("consent.mustAccept")}</p>}
            <Button type="submit" busy={busy} disabled={!healthDoc.id}>{t("common.next")}</Button>
          </>)}
          <p><button type="button" className="btn-secondary" onClick={() => setStage("equipment")}>{t("common.back")}</button></p>
        </form>
      )}

      {stage === "screening" && (
        <form noValidate onSubmit={submitScreening}>
          <h2>{t("screening.title")}</h2>
          <p>{t("screening.intro")}</p>
          {SCREENING_QUESTIONS.map((q) => (
            <fieldset key={q} className="yn"><legend>{t(`screening.q.${q}`)}</legend>
              <label className="check"><input type="radio" name={q} checked={answers[q] === true} onChange={() => setAnswers({ ...answers, [q]: true })} />{t("screening.yes")}</label>
              <label className="check"><input type="radio" name={q} checked={answers[q] === false} onChange={() => setAnswers({ ...answers, [q]: false })} />{t("screening.no")}</label>
            </fieldset>
          ))}
          {fieldErr.screening && <p className="field-error" role="alert">{t("screening.unanswered")}</p>}
          <Button type="submit" busy={busy}>{t("screening.finish")}</Button>
          {decision && <DecisionPanel decision={decision} />}
        </form>
      )}

      {stage === "finish" && (
        <div>
          <h2>{t("onb.finish.title")}</h2>
          <p>{t("onb.finish.body")}</p>
          <p className="muted">{n(STAGES.length)} / {n(STAGES.length)}</p>
          <div className="row"><Button type="button" busy={busy} onClick={complete}>{t("onb.finish.submit")}</Button><ButtonLink href={`/${locale}/plan`} secondary>{t("onb.finish.goPlan")}</ButtonLink></div>
        </div>
      )}
    </Card>
  );
}

export default function OnboardingPage() {
  return <Suspense fallback={<Loading />}><Wizard /></Suspense>;
}

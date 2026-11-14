"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { HealthProfile, SafetyDecision } from "../../../lib/api/generated.ts";
import { permitsPlan } from "../../../lib/plan-view.ts";
import { PAIN_REGIONS } from "../../../lib/workout-log.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, Card, Field, Loading } from "../../../components/ui.tsx";
import { DecisionPanel } from "../../../components/DecisionPanel.tsx";

const PROBLEMS = ["pain", "limited_motion", "diagnosed_injury", "surgery_history", "other"] as const;
const TIMING = ["general", "before", "during", "after"] as const;

/** Pain / condition self-report. The page only records what the user says; the Safety Core alone decides what it means for the plan. */
export default function HealthPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [hp, setHp] = useState<HealthProfile | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [decision, setDecision] = useState<SafetyDecision | null>(null);
  const [region, setRegion] = useState("lower_back");
  const [intensity, setIntensity] = useState("0");
  const [timing, setTiming] = useState<(typeof TIMING)[number]>("general");
  const [problem, setProblem] = useState<(typeof PROBLEMS)[number]>("pain");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");

  async function load() {
    const r = await api.call("API-HEALTH-001");
    if (r.ok) return setHp(r.data);
    if (r.status === 401) return router.replace(`/${locale}/login`);
    setError(r.error); setHp({});
  }
  useEffect(() => { void load(); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api]);

  async function done<T>(r: { ok: boolean; status: number; data?: T; error?: ApiError }, msg: string) {
    setBusy(false);
    if (!r.ok) { if (r.status === 401) return router.replace(`/${locale}/login`); return setError(r.error!); }
    setSaved(msg); await load();
  }
  async function logPain(e: FormEvent) {
    e.preventDefault(); setError(null); setSaved(""); setBusy(true);
    const v = Number(intensity);
    const r = await api.call("API-HEALTH-005", { body: { region, intensity: v, timing } });
    if (r.ok && r.data.decision) setDecision(r.data.decision);
    await done(r, t("health.saved"));
  }
  async function addCondition(e: FormEvent) {
    e.preventDefault(); setError(null); setSaved(""); setBusy(true);
    const r = await api.call("API-HEALTH-002", { body: { region, problem_type: problem } });
    await done(r, t("health.saved"));
  }

  const guidance = region === "chest" ? "wk.pain_stop_chest" : "wk.pain_stop_region";
  return (
    <Card title={t("health.title")}>
      <p className="hint">{t("health.hint")}</p>
      <ApiErrorView error={error} />
      {!hp && !error && <Loading />}
      {hp && (
        <>
          <h2>{t("health.conditions")}</h2>
          {(hp.conditions ?? []).length === 0 ? <p className="muted">{t("health.none")}</p> : (
            <ul className="plain">{hp.conditions!.map((c, i) => <li key={c.id ?? i}>{t(`region.${c.region}`)} — {t(`health.problem.${c.problem_type}`)}{c.self_severity !== undefined && ` (${n(c.self_severity)}/10)`}</li>)}</ul>)}
          {hp.latest_decision && !permitsPlan(hp.latest_decision.status) && !decision && <DecisionPanel decision={hp.latest_decision} />}

          <h2>{t("health.logPain")}</h2>
          <form onSubmit={logPain} noValidate>
            <Field id="region" label={t("wk.painRegion")}>
              <select id="region" value={region} onChange={(e) => setRegion(e.target.value)}>{PAIN_REGIONS.map((r) => <option key={r} value={r}>{t(`region.${r}`)}</option>)}</select>
            </Field>
            <Field id="intensity" label={t("health.intensity")} hint={t("health.intensityHint")}>
              <select id="intensity" value={intensity} onChange={(e) => setIntensity(e.target.value)}>{Array.from({ length: 11 }, (_, i) => <option key={i} value={i}>{n(i)}</option>)}</select>
            </Field>
            <Field id="timing" label={t("health.timing")}>
              <select id="timing" value={timing} onChange={(e) => setTiming(e.target.value as (typeof TIMING)[number])}>{TIMING.map((x) => <option key={x} value={x}>{t(`health.timing.${x}`)}</option>)}</select>
            </Field>
            <Button type="submit" busy={busy}>{t("health.save")}</Button>
          </form>
          {Number(intensity) > 0 && <Alert kind="warning">{t(guidance)}</Alert>}
          {decision && !permitsPlan(decision.status) && <DecisionPanel decision={decision} />}

          <h2>{t("health.addCondition")}</h2>
          <form onSubmit={addCondition} noValidate>
            <Field id="problem" label={t("health.problem")}>
              <select id="problem" value={problem} onChange={(e) => setProblem(e.target.value as (typeof PROBLEMS)[number])}>{PROBLEMS.map((x) => <option key={x} value={x}>{t(`health.problem.${x}`)}</option>)}</select>
            </Field>
            <p className="hint">{t("health.regionShared")}</p>
            <Button type="submit" busy={busy}>{t("health.save")}</Button>
          </form>
          {saved && <Alert kind="success">{saved}</Alert>}
          <p className="muted">{t("health.disclaimer")}</p>
        </>
      )}
    </Card>
  );
}

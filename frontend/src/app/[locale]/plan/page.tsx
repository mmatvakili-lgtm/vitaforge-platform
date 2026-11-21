"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { WorkoutPlan } from "../../../lib/api/generated.ts";
import { currentPlanView, decidePlanView, type PlanView } from "../../../lib/plan-view.ts";
import { safetyReason } from "../../../lib/i18n.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Loading } from "../../../components/ui.tsx";
import { DecisionPanel } from "../../../components/DecisionPanel.tsx";
import { Body3D } from "../../../components/Body3D.tsx";
import { ExerciseAnimById } from "../../../components/ExerciseAnim.tsx";
import { muscleRegion } from "../../../lib/body3d.ts";

function PlanBody({ plan, modified, onSubstitute }: { plan: WorkoutPlan; modified: boolean; onSubstitute: (workoutExerciseId: string, reason: string) => Promise<void> }) {
  const { locale, t, n } = useT();
  const [open, setOpen] = useState<string | null>(null);
  const [dayIdx, setDayIdx] = useState(0);
  const [exSel, setExSel] = useState<string | null>(null);
  const days = plan.days ?? [];
  const day = days[Math.min(dayIdx, Math.max(0, days.length - 1))];
  const regionsOf = (e: { muscles?: string[] }) => (e.muscles ?? []).map((m) => muscleRegion(m)).filter((x): x is string => !!x);
  const dayMuscles = new Set<string>((day?.exercises ?? []).flatMap(regionsOf));
  const selEx = (day?.exercises ?? []).find((e, k) => (e.workout_exercise_id ?? String(k)) === exSel);
  const bodyStatus: Record<string, "focus" | "high"> = {};
  if (selEx) { for (const m of dayMuscles) bodyStatus[m] = "high"; for (const m of regionsOf(selEx)) bodyStatus[m] = "focus"; }
  else for (const m of dayMuscles) bodyStatus[m] = "focus";
  return (
    <div>
      <p className="muted plan-meta">
        {t("plan.version", { n: plan.version_no })}
        {plan.goal && <> · {t("plan.goal")}: {t(`goal.${plan.goal}`) === `goal.${plan.goal}` ? plan.goal : t(`goal.${plan.goal}`)}</>}
        {plan.structure && <> · {t("plan.structure")}: {t(`plan.structure.${plan.structure}`) === `plan.structure.${plan.structure}` ? plan.structure : t(`plan.structure.${plan.structure}`)}</>}
        {plan.confidence && <> · {t("plan.confidence")}: {t(`plan.confidence.${plan.confidence}`)}</>}
      </p>
      {plan.rationale?.content_status !== "published" && <Alert kind="warning"><strong>{t("plan.experimental.title")}</strong><p>{t("plan.experimental.body")}</p></Alert>}
      {modified && <Alert kind="warning">{t("plan.modified")}</Alert>}
      {(() => {
        const rs = (plan.rationale?.reasons ?? []) as string[];
        const ph = rs.find((x) => x.startsWith("phase:"))?.slice(6);
        return ph ? <Alert kind="info"><strong>{t("plan.phase.title")}:</strong> {t(`plan.phase.${ph}`)}{rs.includes("deload:auto:rpe_high") && <> {t("plan.phase.auto")}</>}</Alert> : null;
      })()}
      <div className="plan-split">
        <aside className="plan-body">
          {(selEx ?? day?.exercises?.[0])?.exercise_id && (
            <ExerciseAnimById key={(selEx ?? day?.exercises?.[0])!.exercise_id} exerciseId={(selEx ?? day?.exercises?.[0])!.exercise_id!} muscles={(selEx ?? day?.exercises?.[0])!.muscles} height={190} />
          )}
          <div className="body-stage">
            <Body3D height={300} status={bodyStatus} label={t("plan.bodyAria")} />
            <div className="legend" aria-hidden="true">
              <span><i className="dot" style={{ background: "var(--body-focus)" }} />{exSel ? t("plan.legend.exercise") : t("plan.legend.day")}</span>
              {exSel && dayMuscles.size > 0 && <span><i className="dot" style={{ background: "var(--body-high)" }} />{t("plan.legend.restOfDay")}</span>}
            </div>
          </div>
          <p className="muted body-hint">{t("body3d.hint")}</p>
        </aside>
        <div className="plan-days">
          <div className="day-tabs" role="tablist" aria-label={t("plan.days")}>
            {days.map((d, i) => (
              <button key={d.day_id ?? i} role="tab" type="button" aria-selected={i === dayIdx} className={i === dayIdx ? "on" : ""} onClick={() => { setDayIdx(i); setExSel(null); }}>
                <span className="num">{n(i + 1)}</span><span>{d.title ?? t("plan.day", { n: (d.day_index ?? i) + 1 })}</span>
              </button>
            ))}
          </div>
          {day && (
            <section className="day" key={day.day_id ?? dayIdx}>
              <h2>{day.title ?? t("plan.day", { n: (day.day_index ?? dayIdx) + 1 })}{day.est_minutes !== undefined && <span className="muted"> · {t("plan.minutes", { n: day.est_minutes })}</span>}</h2>
              <div className="chips" aria-label={t("plan.dayMuscles")}>
                {[...dayMuscles].map((m) => <span key={m} className="chip">{t(`muscle.${m}`)}</span>)}
              </div>
              {day.day_id && <ButtonLink href={`/${locale}/workout?day=${day.day_id}`}>{t("plan.start")}</ButtonLink>}
              <ol className="exercises">
                {(day.exercises ?? []).map((e, k) => {
                  const on = exSel === (e.workout_exercise_id ?? String(k));
                  const regs = [...new Set((e.muscles ?? []).map((m) => muscleRegion(m)).filter((x): x is string => !!x))];
                  return (
                    <li key={e.workout_exercise_id ?? k} className={on ? "on" : ""}>
                      <button type="button" className="ex-head" aria-expanded={on} onClick={() => setExSel(on ? null : (e.workout_exercise_id ?? String(k)))}>
                        <span className="num idx">{n(k + 1)}</span>
                        <span className="nm">{e.name}</span>
                        {e.role && <span className="tag">{t(`plan.role.${e.role}`)}</span>}
                        <span className="chips sm">{regs.slice(0, 3).map((m) => <span key={m} className="chip">{t(`muscle.${m}`)}</span>)}</span>
                      </button>
                      {e.exercise_id && <Link className="ex-link" href={`/${locale}/exercises/${e.exercise_id}`}>{t("plan.exerciseDetail")}</Link>}
                      <ul className="plain sets">
                        {(e.sets ?? []).map((st, j) => (
                          <li key={st.set_no ?? j}>
                            {n(st.set_no ?? j + 1)}.{" "}
                            {st.reps_min !== undefined && st.reps_max !== undefined && t("plan.reps", { min: st.reps_min, max: st.reps_max })}
                            {st.duration_sec !== undefined && ` ${n(st.duration_sec)}s`}
                            {st.target_rpe !== undefined && ` · ${t("plan.rpe", { n: st.target_rpe })}`}
                            {st.rest_sec !== undefined && ` · ${t("plan.rest", { n: st.rest_sec })}`}
                          </li>
                        ))}
                      </ul>
                      {e.workout_exercise_id && e.role !== "warmup" && e.role !== "cooldown" && (
                        open === e.workout_exercise_id ? (
                          <div className="row" role="group" aria-label={t("plan.substituteWhy")}>
                            {(["pain", "equipment", "preference", "other"] as const).map((r) => <Button key={r} type="button" onClick={async () => { setOpen(null); await onSubstitute(e.workout_exercise_id!, r); }}>{t(`sub.${r}`)}</Button>)}
                            <Button type="button" onClick={() => setOpen(null)}>{t("sub.cancel")}</Button>
                          </div>
                        ) : <Button type="button" onClick={() => setOpen(e.workout_exercise_id!)}>{t("plan.substitute")}</Button>
                      )}
                    </li>
                  );
                })}
              </ol>
            </section>
          )}
        </div>
      </div>
      <p className="muted">{t("plan.safetyId", { id: plan.safety_decision_id })}</p>
    </div>
  );
}

export default function PlanPage() {
  const { locale, t } = useT();
  const api = useApi();
  const router = useRouter();
  const [view, setView] = useState<PlanView | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(false);
  const [noAlt, setNoAlt] = useState(false);

  const load = useCallback(async () => {
    const r = await api.call("API-WO-002");
    if (r.ok) return setView(currentPlanView(r.data));
    if (r.status === 401) return router.replace(`/${locale}/login`);
    if (r.status === 404) return setView({ kind: "empty" });
    setError(r.error); setView({ kind: "empty" });
  }, [api, router, locale]);
  useEffect(() => { load(); }, [load]);

  async function generate() {
    setBusy(true); setError(null);
    const r = await api.call("API-WO-001", { body: {} });
    setBusy(false);
    if (!r.ok) { if (r.status === 401) return router.replace(`/${locale}/login`); return setError(r.error); }
    setView(decidePlanView(r.data.decision, r.data.plan));
  }

  async function substitute(workoutExerciseId: string, reason: string) {
    if (view?.kind !== "plan" || !view.plan.plan_id) return;
    setBusy(true); setError(null); setNotice(false); setNoAlt(false);
    const r = await api.call("API-WO-004", { path: { plan_id: view.plan.plan_id }, body: { workout_exercise_id: workoutExerciseId, reason: reason as "pain" | "equipment" | "preference" | "other" } });
    setBusy(false);
    if (!r.ok) { if (r.status === 401) return router.replace(`/${locale}/login`); if (r.status === 409) return setNoAlt(true); return setError(r.error); }
    setView({ kind: "plan", plan: r.data, modified: view.modified }); setNotice(true);
  }

  return (
    <Card title={t("plan.title")}>
      <ApiErrorView error={error} />
      {error?.code === "precondition_required" && <ButtonLink href={`/${locale}/onboarding`} secondary>{t("nav.onboarding")}</ButtonLink>}
      {!view && <Loading />}
      {view?.kind === "empty" && <p>{t("plan.empty")}</p>}
      {view?.kind === "plan" && view.decision?.reasons?.some((r) => r.code === "SAF-R021") && (
        <Alert kind="warning">
          <strong>{t("safety.advisory.title")}</strong>
          <p>{t("safety.advisory.body")}</p>
          {view.decision.referral?.urgency === "urgent" && <p>{t("safety.advisory.urgent")}</p>}
          <ul>{(view.decision.reasons ?? []).filter((r) => r.code && r.code !== "SAF-R021").map((r) => <li key={r.code}>{safetyReason(locale, r.code!)}</li>)}</ul>
        </Alert>
      )}
      {view?.kind === "plan" && <PlanBody plan={view.plan} modified={view.modified} onSubstitute={substitute} />}
      {noAlt && <Alert kind="warning">{t("error.no_valid_alternative")}</Alert>}
      {notice && <Alert kind="success">{t("plan.substituted")}</Alert>}
      {view && view.kind !== "plan" && view.kind !== "empty" && <DecisionPanel decision={view.decision} />}
      {view && <Button type="button" busy={busy} onClick={generate}>{view.kind === "plan" ? t("plan.regenerate") : t("plan.generate")}</Button>}
    </Card>
  );
}

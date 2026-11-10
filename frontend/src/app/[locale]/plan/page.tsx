"use client";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { WorkoutPlan } from "../../../lib/api/generated.ts";
import { currentPlanView, decidePlanView, type PlanView } from "../../../lib/plan-view.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Loading } from "../../../components/ui.tsx";
import { DecisionPanel } from "../../../components/DecisionPanel.tsx";

function PlanBody({ plan, modified }: { plan: WorkoutPlan; modified: boolean }) {
  const { t, n } = useT();
  return (
    <div>
      <p className="muted">
        {t("plan.version", { n: plan.version_no })}
        {plan.goal && <> · {t("plan.goal")}: {t(`goal.${plan.goal}`) === `goal.${plan.goal}` ? plan.goal : t(`goal.${plan.goal}`)}</>}
        {plan.structure && <> · {t("plan.structure")}: {t(`plan.structure.${plan.structure}`) === `plan.structure.${plan.structure}` ? plan.structure : t(`plan.structure.${plan.structure}`)}</>}
        {plan.confidence && <> · {t("plan.confidence")}: {t(`plan.confidence.${plan.confidence}`)}</>}
      </p>
      {plan.rationale?.content_status !== "published" && <Alert kind="warning"><strong>{t("plan.experimental.title")}</strong><p>{t("plan.experimental.body")}</p></Alert>}
      {modified && <Alert kind="warning">{t("plan.modified")}</Alert>}
      {(plan.days ?? []).map((d, i) => (
        <section key={d.day_id ?? i} className="day">
          <h2>{d.title ?? t("plan.day", { n: (d.day_index ?? i) + 1 })}{d.est_minutes !== undefined && <span className="muted"> · {t("plan.minutes", { n: d.est_minutes })}</span>}</h2>
          <ol className="exercises">
            {(d.exercises ?? []).map((e, k) => (
              <li key={e.workout_exercise_id ?? k}>
                <strong>{e.name}</strong> {e.role && <span className="tag">{t(`plan.role.${e.role}`)}</span>}
                <ul className="plain sets">
                  {(e.sets ?? []).map((s, j) => (
                    <li key={s.set_no ?? j}>
                      {n(s.set_no ?? j + 1)}.{" "}
                      {s.reps_min !== undefined && s.reps_max !== undefined && t("plan.reps", { min: s.reps_min, max: s.reps_max })}
                      {s.duration_sec !== undefined && ` ${n(s.duration_sec)}s`}
                      {s.target_rpe !== undefined && ` · ${t("plan.rpe", { n: s.target_rpe })}`}
                      {s.rest_sec !== undefined && ` · ${t("plan.rest", { n: s.rest_sec })}`}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </section>
      ))}
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

  return (
    <Card title={t("plan.title")}>
      <ApiErrorView error={error} />
      {error?.code === "precondition_required" && <ButtonLink href={`/${locale}/onboarding`} secondary>{t("nav.onboarding")}</ButtonLink>}
      {!view && <Loading />}
      {view?.kind === "empty" && <p>{t("plan.empty")}</p>}
      {view?.kind === "plan" && <PlanBody plan={view.plan} modified={view.modified} />}
      {view && view.kind !== "plan" && view.kind !== "empty" && <DecisionPanel decision={view.decision} />}
      {view && <Button type="button" busy={busy} onClick={generate}>{view.kind === "plan" ? t("plan.regenerate") : t("plan.generate")}</Button>}
    </Card>
  );
}

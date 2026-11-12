"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { Dashboard, NutritionDaySummary, ProgressReport } from "../../../lib/api/generated.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { ApiErrorView, ButtonLink, Card, Loading } from "../../../components/ui.tsx";
import { DecisionPanel } from "../../../components/DecisionPanel.tsx";

export default function DashboardPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [d, setD] = useState<Dashboard | null>(null);
  const [week, setWeek] = useState<ProgressReport | null>(null);
  const [nut, setNut] = useState<NutritionDaySummary | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  useEffect(() => {
    let live = true;
    Promise.all([api.call("API-DASH-001"), api.call("API-PROG-001")]).then(([a, b]) => {
      if (!live) return;
      if (!a.ok) { if (a.status === 401) return router.replace(`/${locale}/login`); return setError(a.error); }
      setD(a.data); if (b.ok) setWeek(b.data);
    });
    api.call("API-NUT-008").then((r) => { if (live && r.ok) setNut(r.data); });   // absent (no consent/profile/OK result) => the block is simply not shown
    return () => { live = false; };
  }, [api, router, locale]);
  const w = (d?.weekly_summary ?? {}) as { sessions?: number; sets?: number; volume_kg?: number };
  const plan = (d?.current_plan ?? {}) as { version_no?: number };
  return (
    <Card title={t("dash.title")}>
      <ApiErrorView error={error} />
      {!d && !error && <Loading />}
      {d && (
        <>
          {(d.alerts ?? []).length > 0 && (<><h2>{t("dash.alerts")}</h2>{d.alerts!.map((a, i) => <DecisionPanel key={i} decision={a} />)}</>)}
          <h2>{t("dash.week")}</h2>
          <ul className="plain">
            <li>{t("dash.sessions")}: {n(w.sessions ?? 0)}</li>
            <li>{t("dash.sets")}: {n(w.sets ?? 0)}</li>
            <li>{t("dash.volume")}: {n(w.volume_kg ?? 0)}</li>
            {week?.planned_sessions !== undefined && <li>{t("dash.planned", { n: n(week.planned_sessions) })}</li>}
            {week?.adherence_pct !== undefined && <li>{t("dash.adherence", { pct: n(week.adherence_pct) })}</li>}
          </ul>
          <h2>{t("dash.plan")}</h2>
          <p>{plan.version_no !== undefined ? t("dash.version", { n: n(plan.version_no) }) : t("dash.noPlan")}</p>
          {nut && (<><h2>{t("dash.nutrition")}</h2>
            <ul className="plain"><li>{t("nutrient.kcal")}: {n(Math.round(nut.kcal))}</li><li>{t("nut.log.water")}: {n(nut.water_ml)} ml</li><li>{t("dash.meals", { n: nut.meals })}</li></ul>
            <p className="muted">{t("nut.label.estimate")}</p></>)}
          <h2>{t("dash.quick")}</h2>
          <div className="row">
            <ButtonLink href={`/${locale}/plan`}>{t("nav.plan")}</ButtonLink>
            <ButtonLink href={`/${locale}/exercises`} secondary>{t("nav.exercises")}</ButtonLink>
            <ButtonLink href={`/${locale}/nutrition`} secondary>{t("nav.nutrition")}</ButtonLink>
            <ButtonLink href={`/${locale}/history`} secondary>{t("nav.history")}</ButtonLink>
          </div>
        </>
      )}
    </Card>
  );
}

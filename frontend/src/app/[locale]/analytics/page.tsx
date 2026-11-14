"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { Analytics } from "../../../lib/api/generated.ts";
import { insightMessageKey, insightParams, sparkRuns } from "../../../lib/analytics.ts";
import { barPct } from "../../../lib/trends.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { ApiErrorView, Card, Loading } from "../../../components/ui.tsx";

export default function AnalyticsPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    void (async () => {
      const r = await api.call("API-ANALYTICS-001");
      if (r.ok) return setData(r.data);
      if (r.status === 401) return router.replace(`/${locale}/login`);
      setError(r.error);
    })();
  }, [api, locale, router]);

  const label = (k: string, fallback: string) => { const m = t(`muscle.${k}`); return m === `muscle.${k}` ? fallback : m; };
  const maxVol = Math.max(0, ...(data?.weeks ?? []).map((w) => w.volume_kg));
  return (
    <Card title={t("analytics.title")}>
      <ApiErrorView error={error} />
      {!data && !error && <Loading />}
      {data && (
        <>
          <p className="muted">{t("analytics.note")}</p>
          <section aria-label={t("analytics.insights")}>
            <h2>{t("analytics.insights")}</h2>
            <ul className="plain">
              {data.insights.map((i, idx) => {
                const p = insightParams(i.params ?? {});
                if (typeof p.muscle === "string") p.muscle = label(p.muscle, p.muscle);
                return <li key={idx}>{t(insightMessageKey(i.key), p)}</li>;
              })}
            </ul>
          </section>
          <section aria-label={t("analytics.consistency")}>
            <h2>{t("analytics.consistency")}</h2>
            <ul className="plain">
              <li>{t("analytics.streak", { n: n(data.streak_weeks) })}</li>
              <li>{t("analytics.records", { n: n(data.records_4w) })}</li>
              {data.days_since_last !== null && <li>{t("analytics.lastSession", { n: n(data.days_since_last) })}</li>}
            </ul>
          </section>
          <section aria-label={t("analytics.weekly")}>
            <h2>{t("analytics.weekly")}</h2>
            <ol className="bars">
              {data.weeks.map((w) => (
                <li key={w.week_ago} title={`${n(w.volume_kg)} kg · ${n(w.sessions)}`}>
                  <span className="bar" style={{ blockSize: `${barPct(w.volume_kg, maxVol)}%` }} />
                  <span className="sr-only">{`${n(w.volume_kg)} kg · ${n(w.sessions)}`}</span>
                </li>))}
            </ol>
          </section>
          <section aria-label={t("analytics.e1rm")}>
            <h2>{t("analytics.e1rm")}</h2>
            <p className="muted">{t("analytics.e1rmNote")}</p>
            {data.e1rm.length === 0 ? <p className="muted">{t("analytics.empty")}</p> : (
              <ul className="plain">
                {data.e1rm.map((r) => (
                  <li key={r.code}>
                    <strong>{r.name ?? r.code}</strong>: {n(r.latest)} kg
                    {r.change_pct !== null && r.change_pct !== undefined && <span> ({r.change_pct > 0 ? "+" : ""}{n(r.change_pct)}%)</span>}
                    <svg viewBox="0 0 100 20" width="100" height="20" aria-hidden="true" style={{ marginInlineStart: 8 }}>
                      {sparkRuns(r.series, 100, 20).map((pts, i) => <polyline key={i} points={pts} fill="none" stroke="currentColor" strokeWidth="1.5" />)}
                    </svg>
                  </li>))}
              </ul>)}
          </section>
          <section aria-label={t("analytics.muscles")}>
            <h2>{t("analytics.muscles")}</h2>
            {data.muscles.length === 0 ? <p className="muted">{t("analytics.empty")}</p> : (
              <ul className="plain">
                {data.muscles.map((m) => <li key={m.muscle}>{label(m.muscle, m.muscle)}: {n(m.avg_weekly_sets_4w)} {t("analytics.setsPerWeek")} — {t(`analytics.status.${m.status}`)}</li>)}
              </ul>)}
          </section>
        </>)}
    </Card>
  );
}

"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { Analytics } from "../../../lib/api/generated.ts";
import { insightMessageKey, insightParams, sparkRuns } from "../../../lib/analytics.ts";
import { barPct } from "../../../lib/trends.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { ApiErrorView, Card, Loading, CountUp } from "../../../components/ui.tsx";
import { Body3D, type RegionStatus } from "../../../components/Body3D.tsx";

export default function AnalyticsPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [picked, setPicked] = useState<string | null>(null);

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
          <section aria-label={t("analytics.body")}>
            <h2>{t("analytics.body")}</h2>
            <div className="body-stage">
              <Body3D status={Object.fromEntries(data.muscles.map((m) => [m.muscle, m.status as RegionStatus]))} selected={picked} onPick={setPicked} label={t("analytics.bodyAria")} />
              <div className="legend" aria-hidden="true">
                {(["low", "ok", "high"] as const).map((k) => <span key={k}><i className="dot" style={{ background: `var(--body-${k})` }} />{t(`analytics.legend.${k}`)}</span>)}
                <span><i className="dot" style={{ background: "var(--body-base)" }} />{t("analytics.legend.none")}</span>
              </div>
            </div>
            <p className="muted">{t("analytics.bodyHint")}</p>
            {picked && (() => {
              const m = data.muscles.find((x) => x.muscle === picked);
              const name = label(picked, picked);
              return <p role="status">{m ? t("analytics.picked", { muscle: name, avg: n(m.avg_weekly_sets_4w) }) : t("analytics.pickedNone", { muscle: name })}</p>;
            })()}
          </section>
          <section aria-label={t("analytics.insights")}>
            <h2>{t("analytics.insights")}</h2>
            <ul className="plain insights">
              {data.insights.map((i, idx) => {
                const p = insightParams(i.params ?? {});
                if (typeof p.muscle === "string") p.muscle = label(p.muscle, p.muscle);
                return <li key={idx}><i aria-hidden="true">✦</i><span>{t(insightMessageKey(i.key), p)}</span></li>;
              })}
            </ul>
          </section>
          <section aria-label={t("analytics.consistency")}>
            <h2>{t("analytics.consistency")}</h2>
            <div className="stat-grid">
              <div className="stat"><span className="num"><CountUp value={data.streak_weeks} /></span><small>{t("analytics.streakLabel")}</small></div>
              <div className="stat"><span className="num"><CountUp value={data.records_4w} /></span><small>{t("analytics.recordsLabel")}</small></div>
              {data.days_since_last !== null && <div className="stat"><span className="num">{n(data.days_since_last)}</span><small>{t("analytics.lastLabel")}</small></div>}
            </div>
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
              <ul className="plain e1">
                {data.e1rm.map((r) => (
                  <li key={r.code}>
                    <strong>{r.name ?? r.code}</strong>
                    <span className="e1-val"><b className="num">{n(r.latest)}</b> kg</span>
                    {r.change_pct !== null && r.change_pct !== undefined && <span className={r.change_pct > 0 ? "chg up" : r.change_pct < 0 ? "chg down" : "chg"}>{r.change_pct > 0 ? "▲ +" : r.change_pct < 0 ? "▼ " : "● "}{n(r.change_pct)}%</span>}
                    <svg viewBox="0 0 100 20" width="100%" height="36" preserveAspectRatio="none" aria-hidden="true">
                      {sparkRuns(r.series, 100, 20).map((pts, i) => <polyline key={i} points={pts} pathLength={1} className="spark" fill="none" stroke="currentColor" strokeWidth="1.5" />)}
                    </svg>
                  </li>))}
              </ul>)}
          </section>
          <section aria-label={t("analytics.muscles")}>
            <h2>{t("analytics.muscles")}</h2>
            {data.muscles.length === 0 ? <p className="muted">{t("analytics.empty")}</p> : (
              <ul className="plain mmeters">
                {data.muscles.map((m) => (
                  <li key={m.muscle} data-status={m.status}>
                    <div className="mm-head"><strong>{label(m.muscle, m.muscle)}</strong><span>{n(m.avg_weekly_sets_4w)} {t("analytics.setsPerWeek")}</span></div>
                    <div className="mm-track" aria-hidden="true"><i style={{ inlineSize: `${Math.min(100, (m.avg_weekly_sets_4w / 20) * 100)}%` }} /></div>
                    <small className="mm-tag">{m.status === "low" ? "▼ " : m.status === "high" ? "▲ " : "● "}{t(`analytics.status.${m.status}`)}</small>
                  </li>))}
              </ul>)}
          </section>
        </>)}
    </Card>
  );
}

"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { WorkoutSession } from "../../../lib/api/generated.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { barPct, weeklyBuckets } from "../../../lib/trends.ts";
import { ApiErrorView, Card, Loading } from "../../../components/ui.tsx";

export default function HistoryPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [rows, setRows] = useState<WorkoutSession[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  useEffect(() => {
    let live = true;
    api.call("API-LOG-004").then((r) => {
      if (!live) return;
      if (r.ok) return setRows([...r.data].sort((a, b) => String(b.started_at).localeCompare(String(a.started_at))));
      if (r.status === 401) return router.replace(`/${locale}/login`);
      setError(r.error); setRows([]);
    });
    return () => { live = false; };
  }, [api, router, locale]);
  return (
    <Card title={t("hist.title")}>
      <ApiErrorView error={error} />
      {!rows && <Loading />}
      {rows && rows.length === 0 && !error && <p>{t("hist.empty")}</p>}
      {rows && rows.length > 0 && (() => {
        const wk = weeklyBuckets(rows, new Date()); const max = Math.max(...wk.map((b) => b.volumeKg));
        const fmt = new Intl.DateTimeFormat(locale === "fa" ? "fa-IR" : "en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
        return (
          <section aria-label={t("hist.trend")}>
            <h2>{t("hist.trend")}</h2>
            <ol className="bars">
              {wk.map((b) => (
                <li key={b.weekStart} title={t("hist.trend.item", { sessions: b.sessions, kg: Math.round(b.volumeKg) })}>
                  <span className="bar" style={{ blockSize: `${barPct(b.volumeKg, max)}%` }} />
                  <span className="muted bar-label"><time dateTime={b.weekStart}>{fmt.format(new Date(b.weekStart))}</time></span>
                  <span className="sr-only">{t("hist.trend.item", { sessions: b.sessions, kg: Math.round(b.volumeKg) })}</span>
                </li>))}
            </ol>
            <p className="muted">{t("hist.trend.hint")}</p>
          </section>);
      })()}
      <ul className="plain">
        {(rows ?? []).map((s) => (
          <li key={s.id} className="doc">
            <strong>{s.day_title || t("wk.title")}</strong> <span className="tag">{t(`hist.status.${s.status}`)}</span>
            <div className="muted">
              <time dateTime={s.started_at}>{s.started_at ? new Intl.DateTimeFormat(locale === "fa" ? "fa-IR" : "en-GB", { dateStyle: "medium" }).format(new Date(s.started_at)) : ""}</time>
              {" · "}{t("hist.sets", { n: n(s.sets_done ?? 0) })}{" · "}{t("hist.volume", { kg: n(s.volume_kg ?? 0) })}
              {s.duration_min !== undefined && <> · {t("hist.minutes", { n: n(s.duration_min) })}</>}
              {s.aborted_reason === "pain" && <> · {t("hist.pain")}</>}
            </div>
            {s.status === "in_progress" && <Link href={`/${locale}/plan`}>{t("hist.continue")}</Link>}
          </li>
        ))}
      </ul>
    </Card>
  );
}

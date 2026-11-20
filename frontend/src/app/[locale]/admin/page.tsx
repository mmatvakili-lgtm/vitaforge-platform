"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { adminCall } from "../../../lib/admin.ts";
import { barHeights, fmtBytes, pct, sumCounts, type DayCount } from "../../../lib/adminStats.ts";
import { useT } from "../../../lib/react/context.tsx";
import { useStaffRole } from "../../../components/admin/AdminShell.tsx";

interface Overview {
  generated_at: number;
  users: { total: number; verified: number; roles: Record<string, number>; locales: Record<string, number>; joined_per_day: DayCount[] };
  activity: { assessments: number; plans: number; workout_sessions: number; pain_logs: number };
  content: { exercises_by_status: Record<string, number>; media_overrides: number; uploaded_files: number; uploaded_bytes: number; announcement_active: boolean };
  admin_actions_per_day: DayCount[];
}

function Bars({ series, label, locale }: { series: DayCount[]; label: string; locale: string }) {
  const h = barHeights(series);
  const fmt = new Intl.DateTimeFormat(locale, { month: "short", day: "numeric", timeZone: "UTC" });
  return (
    <div className="adm-bars" role="img" aria-label={`${label}: ${sumCounts(series)}`}>
      {series.map((d, i) => (
        <div key={d.day} className="adm-bar" title={`${fmt.format(new Date(d.day * 1000))}: ${d.count}`}>
          <i style={{ blockSize: `${Math.max(h[i] * 100, d.count > 0 ? 6 : 2)}%` }} className={d.count > 0 ? "hot" : ""} />
        </div>))}
    </div>
  );
}

export default function AdminDashboard() {
  const { locale, t, n } = useT();
  const role = useStaffRole();
  const [o, setO] = useState<Overview | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => { adminCall<Overview>("GET", "/admin/overview").then((r) => (r.ok ? setO(r.data) : setFailed(true))); }, []);
  const base = `/${locale}/admin`;

  if (failed) return <p className="alert alert-error" role="alert">{t("admin.error")}</p>;
  if (!o) return <div className="adm-skel" aria-busy="true"><span /><span /><span /><span /></div>;
  const statuses = Object.entries(o.content.exercises_by_status);
  const totalEx = statuses.reduce((a, [, c]) => a + c, 0);
  const stat = (v: number | string, l: string, sub?: string) => (
    <div className="adm-stat"><span className="adm-stat-v num">{typeof v === "number" ? n(v) : v}</span><span className="adm-stat-l">{l}</span>{sub && <span className="adm-stat-s">{sub}</span>}</div>);
  return (
    <>
      <section className="adm-stats" aria-label={t("admin.dash.numbers")}>
        {stat(o.users.total, t("admin.dash.users"), t("admin.dash.verified", { p: pct(o.users.verified, o.users.total) }))}
        {stat(o.activity.plans, t("admin.dash.plans"))}
        {stat(o.activity.workout_sessions, t("admin.dash.sessions"))}
        {stat(o.activity.assessments, t("admin.dash.assessments"))}
      </section>

      <div className="adm-grid">
        <section className="adm-panel">
          <header><h2>{t("admin.dash.joined")}</h2><span className="adm-pill">{n(sumCounts(o.users.joined_per_day))}</span></header>
          <Bars series={o.users.joined_per_day} label={t("admin.dash.joined")} locale={locale} />
          <p className="adm-foot">{t("admin.dash.range", { d: o.users.joined_per_day.length })}</p>
        </section>

        {role === "super_admin" && (
          <section className="adm-panel">
            <header><h2>{t("admin.dash.actions")}</h2><span className="adm-pill">{n(sumCounts(o.admin_actions_per_day))}</span></header>
            <Bars series={o.admin_actions_per_day} label={t("admin.dash.actions")} locale={locale} />
            <p className="adm-foot"><Link href={`${base}/staff`}>{t("admin.dash.openAudit")}</Link></p>
          </section>)}

        <section className="adm-panel">
          <header><h2>{t("admin.dash.library")}</h2><span className="adm-pill">{n(totalEx)}</span></header>
          {totalEx > 0 ? (
            <>
              <div className="adm-stack" role="img" aria-label={statuses.map(([s, c]) => `${s}: ${c}`).join(", ")}>
                {statuses.map(([s, c]) => <i key={s} data-s={s} style={{ flexGrow: c }} title={`${s}: ${c}`} />)}
              </div>
              <ul className="adm-legend">{statuses.map(([s, c]) => <li key={s}><i data-s={s} /> <bdi dir="ltr">{s}</bdi> <b className="num">{n(c)}</b></li>)}</ul>
            </>) : <p className="muted">{t("admin.dash.noLibrary")}</p>}
        </section>

        <section className="adm-panel">
          <header><h2>{t("admin.dash.content")}</h2></header>
          <dl className="adm-kv">
            <div><dt>{t("admin.dash.overrides")}</dt><dd className="num">{n(o.content.media_overrides)}</dd></div>
            <div><dt>{t("admin.dash.files")}</dt><dd className="num">{n(o.content.uploaded_files)} <small>({fmtBytes(o.content.uploaded_bytes)})</small></dd></div>
            <div><dt>{t("admin.dash.announce")}</dt><dd><span className={o.content.announcement_active ? "adm-dot on" : "adm-dot"} />{o.content.announcement_active ? t("admin.dash.on") : t("admin.dash.off")}</dd></div>
            <div><dt>{t("admin.dash.locales")}</dt><dd className="num">fa {n(o.users.locales.fa ?? 0)} · en {n(o.users.locales.en ?? 0)}</dd></div>
          </dl>
        </section>
      </div>

      <section className="adm-quick" aria-label={t("admin.dash.quick")}>
        <Link href={`${base}/media`}><b>{t("admin.nav.media")}</b><span>{t("admin.dash.q.media")}</span></Link>
        <Link href={`${base}/announcement`}><b>{t("admin.nav.announce")}</b><span>{t("admin.dash.q.announce")}</span></Link>
        <Link href={`${base}/review`}><b>{t("admin.nav.review")}</b><span>{t("admin.dash.q.review")}</span></Link>
      </section>
      <p className="adm-foot">{t("admin.dash.privacy")}</p>
    </>
  );
}

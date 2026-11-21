"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { Analytics, AssessmentResult, Dashboard, NutritionDaySummary, Profile, ProgressReport, WorkoutPlan, WorkoutSession } from "../../../lib/api/generated.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { ApiErrorView, ButtonLink, Loading, CountUp, Flame } from "../../../components/ui.tsx";
import { DecisionPanel } from "../../../components/DecisionPanel.tsx";
import { Body3D, type RegionStatus } from "../../../components/Body3D.tsx";
import { muscleRegion } from "../../../lib/body3d.ts";
import { journey, pickTodayDay } from "../../../lib/journey.ts";

/** Weekly sessions as a progress ring; with no planned target it shows the count alone. */
function Ring({ value, total, label }: { value: number; total: number; label: string }) {
  const { n } = useT();
  const R = 42, C = 2 * Math.PI * R;
  const [armed, setArmed] = useState(false);
  useEffect(() => { const id = requestAnimationFrame(() => setArmed(true)); return () => cancelAnimationFrame(id); }, []);
  const f = total > 0 ? Math.min(1, value / total) : value > 0 ? 1 : 0;
  return (
    <div className="ring" role="img" aria-label={`${label}: ${value}${total ? ` / ${total}` : ""}`}>
      <svg viewBox="0 0 100 100" aria-hidden="true">
        <defs><linearGradient id="ringg" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stopColor="var(--heat-1)" /><stop offset=".6" stopColor="var(--heat-2)" /><stop offset="1" stopColor="var(--heat-3)" /></linearGradient></defs>
        <circle cx="50" cy="50" r={R} className="ring-bg" />
        <circle cx="50" cy="50" r={R} className="ring-fg" strokeDasharray={C} strokeDashoffset={C * (1 - (armed ? f : 0))} transform="rotate(-90 50 50)" />
      </svg>
      <span className="ring-n num"><Cu v={value} />{total > 0 && <small>/{n(total)}</small>}</span>
      <span className="ring-l">{label}</span>
    </div>
  );
}

function Cu({ v }: { v: number }) { return v === 0 ? <span className="zero">—</span> : <CountUp value={v} />; }

export default function TodayPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [d, setD] = useState<Dashboard | null>(null);
  const [week, setWeek] = useState<ProgressReport | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [assess, setAssess] = useState<AssessmentResult | null>(null);
  const [plan, setPlan] = useState<WorkoutPlan | null>(null);
  const [sessions, setSessions] = useState<WorkoutSession[]>([]);
  const [tgLinked, setTgLinked] = useState<boolean | null>(null);
  const [nudgeOff, setNudgeOff] = useState(true);
  const [nut, setNut] = useState<NutritionDaySummary | null>(null);
  const [an, setAn] = useState<Analytics | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let live = true;
    Promise.all([api.call("API-DASH-001"), api.call("API-PROG-001"), api.call("API-PRO-001"), api.call("API-ASSESS-001"), api.call("API-WO-002"), api.call("API-LOG-004", { query: { page_size: 50 } })]).then(([a, b, p, s, w, l]) => {
      if (!live) return;
      if (!a.ok) { if (a.status === 401) return router.replace(`/${locale}/login`); return setError(a.error); }
      setD(a.data);
      if (b.ok) setWeek(b.data);
      if (p.ok) setProfile(p.data);
      if (s.ok) setAssess(s.data);
      if (w.ok && Array.isArray((w.data as WorkoutPlan).days)) setPlan(w.data);   // 404 = no plan yet: that is a normal state, not an error
      if (l.ok && Array.isArray(l.data)) setSessions(l.data);
    });
    api.call("API-ANALYTICS-001").then((r) => { if (live && r.ok) setAn(r.data); });   // decorative: the hub works without it
    api.call("API-NUT-008").then((r) => { if (live && r.ok) setNut(r.data); });
    api.call("API-TG-002").then((r) => { if (live && r.ok) setTgLinked(r.data.linked); });
    try { setNudgeOff(localStorage.getItem("vf-tg-nudge") === "off"); } catch { setNudgeOff(false); }
    return () => { live = false; };
  }, [api, router, locale]);

  const w = (d?.weekly_summary ?? {}) as { sessions?: number; sets?: number; volume_kg?: number };
  const lastTitle = useMemo(() => [...sessions].sort((x, y) => (y.started_at ?? "").localeCompare(x.started_at ?? ""))[0]?.day_title, [sessions]);
  const today = useMemo(() => pickTodayDay(plan?.days ?? [], lastTitle), [plan, lastTitle]);
  const j = journey({
    onboardingDone: profile?.onboarding_status === "completed",
    assessed: !!assess?.assessed_at,
    hasPlan: !!plan,
    totalSessions: sessions.length,
    sessionsThisWeek: w.sessions ?? 0,
    plannedPerWeek: week?.planned_sessions ?? 0,
  });
  const focus: Record<string, RegionStatus> = {};
  for (const e of today?.exercises ?? []) for (const m of e.muscles ?? []) { const r = muscleRegion(m); if (r) focus[r] = "focus"; }
  const hasFocus = Object.keys(focus).length > 0;
  const nextHref = j.next === "train" && today?.day_id ? `/${locale}/workout?day=${today.day_id}` : `/${locale}/${j.steps.find((s) => s.key === j.next)!.href}`;
  const name = profile?.display_name;
  const last7 = useMemo(() => {
    const fmt = new Intl.DateTimeFormat(locale, { weekday: "narrow" });
    const days = new Set(sessions.map((x) => (x.started_at ?? "").slice(0, 10)));
    return Array.from({ length: 7 }, (_, i) => {
      const dt = new Date(); dt.setDate(dt.getDate() - (6 - i));
      const key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
      return { key, label: fmt.format(dt), done: days.has(key), today: i === 6 };
    });
  }, [sessions, locale]);

  return (
    <div className="today">
      <ApiErrorView error={error} />
      {!d && !error && <Loading />}
      {d && (
        <>
          <header className="today-head">
            <div>
              <p className="today-date">{new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long" }).format(new Date())}</p>
              <h1>{name ? t("today.greet", { name }) : t("today.greetAnon")}</h1>
            </div>
            <Ring value={w.sessions ?? 0} total={week?.planned_sessions ?? 0} label={t("dash.sessions")} />
          </header>

          {(d.alerts ?? []).length > 0 && (<section className="card">{d.alerts!.map((a, i) => <DecisionPanel key={i} decision={a} />)}</section>)}

          {tgLinked === false && !nudgeOff && (
            <aside className="nudge">
              <div><strong>{t("tg.nudge.title")}</strong><p className="muted">{t("tg.nudge.body")}</p></div>
              <Link href={`/${locale}/profile#telegram`} className="btn">{t("tg.nudge.cta")}</Link>
              <button type="button" className="x" onClick={() => { setNudgeOff(true); try { localStorage.setItem("vf-tg-nudge", "off"); } catch { /* optional */ } }}>{t("tg.nudge.later")}</button>
            </aside>
          )}

          <ol className="journey" aria-label={t("today.journey")}>
            {j.steps.map((s) => (
              <li key={s.key} className={s.done ? "done" : s.key === j.next ? "now" : ""} aria-current={s.key === j.next ? "step" : undefined}>
                <Link href={`/${locale}/${s.href}`}><i aria-hidden="true">{s.done ? "✓" : ""}</i><span>{t(`journey.step.${s.key}`)}</span></Link>
              </li>
            ))}
          </ol>

          <section className="card next">
            <div className="next-copy">
              <p className="kicker">{t("today.progress", { done: n(j.doneCount), total: n(j.steps.length) })}</p>
              <h2>{t(`journey.next.${j.next}.title`)}</h2>
              <p className="lede">{t(`journey.next.${j.next}.body`, { title: today?.title ?? "" })}</p>
              {j.next === "train" && today && (
                <p className="muted">
                  {today.est_minutes !== undefined && <>{t("today.minutes", { n: n(today.est_minutes) })} · </>}
                  {t("today.exercises", { n: n((today.exercises ?? []).filter((e) => e.role !== "warmup" && e.role !== "cooldown").length) })}
                </p>
              )}
              <Link href={nextHref} className="btn cta">{t(`journey.next.${j.next}.cta`)}</Link>
            </div>
            {j.next === "train" && hasFocus && (
              <div className="body-stage next-body">
                <Body3D height={240} status={focus} label={t("plan.bodyAria")} />
                <div className="legend" aria-hidden="true"><span>{t("today.target")}</span></div>
              </div>
            )}
          </section>

          {j.next === "train" && today && (
            <ol className="today-list">
              {(today.exercises ?? []).filter((e) => e.role !== "warmup" && e.role !== "cooldown").map((e, k) => (
                <li key={e.workout_exercise_id ?? k}>
                  <span className="num idx">{n(k + 1)}</span>
                  <span className="nm">{e.name}</span>
                  <span className="num sc">{(e.sets ?? []).length}×{e.sets?.[0]?.reps_min !== undefined ? `${e.sets![0].reps_min}–${e.sets![0].reps_max}` : e.sets?.[0]?.duration_sec ? `${e.sets![0].duration_sec}s` : ""}</span>
                </li>
              ))}
            </ol>
          )}

          <h2 className="sec">{t("today.week")}</h2>
          <ol className="wstrip" aria-hidden="true">
            {last7.map((x) => (
              <li key={x.key} className={`${x.done ? "done" : ""} ${x.today ? "today" : ""}`}>
                <i />
                <small>{x.label}</small>
              </li>
            ))}
          </ol>
          <div className="stat-grid">
            <div className="stat"><span className="num"><Cu v={w.sessions ?? 0} />{week?.planned_sessions ? <small> / {n(week.planned_sessions)}</small> : null}</span><small>{t("dash.sessions")}</small></div>
            <div className="stat"><span className="num">{(an?.streak_weeks ?? 0) > 0 && <Flame />}<Cu v={an?.streak_weeks ?? 0} /></span><small>{t("today.streak")}</small></div>
            <div className="stat"><span className="num"><Cu v={an?.records_4w ?? 0} /></span><small>{t("today.records")}</small></div>
            {an?.days_since_last != null && <div className="stat"><span className="num">{n(an.days_since_last)}</span><small>{t("today.daysSince")}</small></div>}
          </div>

          {an && an.muscles.length > 0 && (
            <details className="card fold">
              <summary>{t("analytics.title")}</summary>
              <div className="body-stage">
                <Body3D height={300} status={Object.fromEntries(an.muscles.map((m) => [m.muscle, m.status as RegionStatus]))} label={t("analytics.bodyAria")} />
                <div className="legend" aria-hidden="true">
                  {(["low", "ok", "high"] as const).map((k) => <span key={k}><i className="dot" style={{ background: `var(--body-${k})` }} />{t(`analytics.legend.${k}`)}</span>)}
                </div>
              </div>
              <ButtonLink href={`/${locale}/analytics`} secondary>{t("today.more")}</ButtonLink>
            </details>
          )}

          {nut && (
            <section className="card">
              <h2>{t("dash.nutrition")}</h2>
              <div className="stat-grid">
                <div className="stat"><span className="num"><Cu v={Math.round(nut.kcal)} /></span><small>{t("nutrient.kcal")}</small></div>
                <div className="stat"><span className="num">{n(nut.water_ml)}</span><small>{t("nut.log.water")} (ml)</small></div>
                <div className="stat"><span className="num"><Cu v={nut.meals} /></span><small>{t("today.meals")}</small></div>
              </div>
              <p className="muted">{t("nut.label.estimate")}</p>
              <ButtonLink href={`/${locale}/nutrition`} secondary>{t("nav.nutrition")}</ButtonLink>
            </section>
          )}
        </>
      )}
    </div>
  );
}

"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import type { ApiError } from "../../../lib/api/client.ts";
import type { SessionSummary, WorkoutDay, WorkoutSession } from "../../../lib/api/generated.ts";
import { PAIN_REGIONS, buildSetLog, finishRequest, isLogged, newUuid, nextSet, plannedSets, progress, skipSetLog, type PlannedSet, type SetDraft } from "../../../lib/workout-log.ts";
import { useApi, useT } from "../../../lib/react/context.tsx";
import { Alert, ApiErrorView, Button, ButtonLink, Card, Field, Loading } from "../../../components/ui.tsx";
import { Progression } from "../../../components/Progression.tsx";

const EMPTY: SetDraft = { reps: "", load: "", rpe: "" };

export default function WorkoutPage() {
  const { locale, t, n } = useT();
  const api = useApi();
  const router = useRouter();
  const [dayId, setDayId] = useState<string | null>(null);
  const [session, setSession] = useState<WorkoutSession | undefined>();
  const [day, setDay] = useState<WorkoutDay | null | undefined>(undefined);       // undefined = loading, null = not found
  const [draft, setDraft] = useState<SetDraft>(EMPTY);
  const [fieldErr, setFieldErr] = useState<Record<string, string>>({});
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);
  const [pr, setPr] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [difficulty, setDifficulty] = useState("");
  const [notes, setNotes] = useState("");
  const [pain, setPain] = useState(false);
  const [painRegion, setPainRegion] = useState("");
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const pending = useRef<{ key: string; uuid: string } | null>(null);              // one client_uuid per set attempt => retries are idempotent

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    setDayId(q.get("day") ?? ""); const s = q.get("session");
    api.call("API-WO-002").then(async (r) => {
      if (!r.ok) { if (r.status === 401) return router.replace(`/${locale}/login`); setError(r.error); return setDay(null); }
      const d = (r.data.days ?? []).find((x) => x.day_id === q.get("day")) ?? null;
      setDay(d);
      if (s) {                                                                       // resume: the session list carries its logged sets
        const list = await api.call("API-LOG-004");
        if (list.ok) setSession(list.data.find((x) => x.id === s));
      }
    });
  }, [api, router, locale]);

  const sets = useMemo(() => (day ? plannedSets(day) : []), [day]);
  const prog = progress(session, sets);
  const next = nextSet(session, sets);
  const finished = session !== undefined && session.status !== "in_progress";

  async function start() {
    if (!dayId) return;
    setBusy(true); setError(null);
    const r = await api.call("API-LOG-001", { body: { day_id: dayId } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setSession(r.data);
    router.replace(`/${locale}/workout?day=${dayId}&session=${r.data.id}`);
  }

  const refresh = useCallback(async (id: string) => {
    const list = await api.call("API-LOG-004");
    if (list.ok) setSession(list.data.find((x) => x.id === id));
  }, [api]);

  async function submitSet(p: PlannedSet, skip: boolean) {
    if (!session?.id) return;
    let body;
    if (skip) body = skipSetLog(p, "");
    else { const b = buildSetLog(p, draft, ""); if (!b.ok) return setFieldErr(b.errors); body = b.body; }
    setFieldErr({}); setBusy(true); setError(null); setPr(false);
    const key = `${p.exerciseId}:${p.setNo}:${skip}:${JSON.stringify(draft)}`;
    if (pending.current?.key !== key) pending.current = { key, uuid: newUuid() };  // same attempt => same uuid, even after a network failure
    const r = await api.call("API-LOG-002", { path: { session_id: session.id }, body: { ...body, client_uuid: pending.current.uuid } });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    pending.current = null; setDraft(EMPTY); setPr(Boolean(r.data.personal_record));
    await refresh(session.id);
  }

  async function finish(e: FormEvent) {
    e.preventDefault();
    if (!session?.id) return;
    setBusy(true); setError(null);
    const r = await api.call("API-LOG-003", { path: { session_id: session.id }, body: finishRequest({ difficulty, stoppedForPain: pain, painRegion, notes }) });
    setBusy(false);
    if (!r.ok) return setError(r.error);
    setSummary(r.data); await refresh(session.id);
  }

  if (day === undefined || dayId === null) return <Card title={t("wk.title")}><Loading /></Card>;
  if (!dayId) return <Card title={t("wk.title")}><p>{t("wk.noDay")}</p><ButtonLink href={`/${locale}/plan`}>{t("nav.plan")}</ButtonLink></Card>;
  if (day === null) return <Card title={t("wk.title")}><ApiErrorView error={error} /><Alert>{t("wk.dayMissing")}</Alert><ButtonLink href={`/${locale}/plan`}>{t("nav.plan")}</ButtonLink></Card>;

  if (summary || (finished && session)) {
    const s = summary;
    return (
      <Card title={t("wk.summary")}>
        {session?.aborted_reason === "pain" && <Alert kind="warning">{t("wk.painWarn")}</Alert>}
        {s?.safety_followup && <Alert kind="warning">{t(`wk.${s.safety_followup.message_key}`)}</Alert>}
        <p>{t("wk.sets", { n: n(s?.sets_done ?? session?.sets_done ?? 0) })} · {t("wk.volume", { kg: n(s?.volume_kg ?? session?.volume_kg ?? 0) })}{(s?.duration_min ?? session?.duration_min) !== undefined && <> · {t("wk.minutes", { n: n((s?.duration_min ?? session?.duration_min) as number) })}</>}</p>
        <div className="row"><ButtonLink href={`/${locale}/history`}>{t("wk.toHistory")}</ButtonLink><ButtonLink href={`/${locale}/plan`} secondary>{t("nav.plan")}</ButtonLink></div>
      </Card>
    );
  }

  return (
    <Card title={day.title ?? t("wk.title")}>
      <ApiErrorView error={error} />
      {!session && <Progression names={Object.fromEntries((day.exercises ?? []).map((x) => [x.exercise_id ?? "", x.name ?? ""]))} />}
      {!session && <Button type="button" busy={busy} onClick={start}>{t("wk.start")}</Button>}
      {session && (
        <>
          <p className="muted" aria-live="polite">{t("wk.progress", { done: n(prog.done), total: n(prog.total) })}</p>
          <progress value={prog.done} max={Math.max(1, prog.total)} aria-label={t("wk.progress", { done: n(prog.done), total: n(prog.total) })} />
          {pr && <Alert kind="success">{t("wk.pr")}</Alert>}
          {next && !finishing && (
            <section className="day" aria-labelledby="cur">
              <h2 id="cur">{next.name} · {t("wk.set", { n: n(next.setNo) })}</h2>
              <p className="muted">
                {next.repsMin !== undefined && next.repsMax !== undefined && t("wk.target", { reps: `${n(next.repsMin)}–${n(next.repsMax)}` })}
                {next.durationSec !== undefined && next.repsMin === undefined && t("wk.targetTime", { sec: n(next.durationSec) })}
                {next.restSec !== undefined && <> · {t("wk.rest", { n: n(next.restSec) })}</>}
              </p>
              <form onSubmit={(e) => { e.preventDefault(); submitSet(next, false); }} noValidate>
                {!(next.durationSec !== undefined && next.repsMin === undefined) && (
                  <Field id="reps" label={t("wk.reps")} error={fieldErr.reps ? t("wk.field.reps") : undefined}><input id="reps" inputMode="numeric" dir="ltr" value={draft.reps} onChange={(e) => setDraft({ ...draft, reps: e.target.value })} /></Field>
                )}
                <Field id="load" label={t("wk.load")} error={fieldErr.load ? t("wk.field.load") : undefined}><input id="load" inputMode="decimal" dir="ltr" value={draft.load} onChange={(e) => setDraft({ ...draft, load: e.target.value })} /></Field>
                <Field id="rpe" label={t("wk.rpe")} error={fieldErr.rpe ? t("wk.field.rpe") : undefined}><input id="rpe" inputMode="decimal" dir="ltr" value={draft.rpe} onChange={(e) => setDraft({ ...draft, rpe: e.target.value })} /></Field>
                <div className="row">
                  <Button type="submit" busy={busy}>{t("wk.log")}</Button>
                  <Button type="button" busy={busy} onClick={() => submitSet(next, true)}>{t("wk.skip")}</Button>
                </div>
              </form>
            </section>
          )}
          <ul className="plain sets">
            {sets.map((p) => <li key={`${p.exerciseId}:${p.setNo}`}>{isLogged(session, p) ? "✓" : "○"} {p.name} · {t("wk.set", { n: n(p.setNo) })}</li>)}
          </ul>
          {!finishing && <Button type="button" onClick={() => setFinishing(true)}>{t("wk.finish")}</Button>}
          {finishing && (
            <form onSubmit={finish} noValidate>
              <Field id="difficulty" label={t("wk.difficulty")}><input id="difficulty" inputMode="numeric" dir="ltr" value={difficulty} onChange={(e) => setDifficulty(e.target.value)} /></Field>
              <Field id="notes" label={t("wk.notes")}><textarea id="notes" maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
              <label className="check"><input type="checkbox" checked={pain} onChange={(e) => setPain(e.target.checked)} /> {t("wk.pain")}</label>
              {pain && (
                <Field id="pain-region" label={t("wk.painRegion")}>
                  <select id="pain-region" value={painRegion} onChange={(e) => setPainRegion(e.target.value)}>
                    <option value="">—</option>
                    {PAIN_REGIONS.map((r) => <option key={r} value={r}>{t(`region.${r}`)}</option>)}
                  </select>
                </Field>
              )}
              {pain && <Alert kind="warning">{t("wk.painWarn")}</Alert>}
              <div className="row"><Button type="submit" busy={busy}>{t("wk.finish")}</Button><Button type="button" onClick={() => setFinishing(false)}>{t("sub.cancel")}</Button></div>
            </form>
          )}
        </>
      )}
      <p><Link href={`/${locale}/plan`}>{t("nav.plan")}</Link></p>
    </Card>
  );
}

// Pure workout-logging logic (validated against the server rules in app_services/workouts.py::log_set). No React, no fetch.
import { normalizeDigits } from "./i18n.ts";
import type { SetLogRequest, SessionFinishRequest, WorkoutDay, WorkoutSession } from "./api/generated.ts";

export type SetDraft = { reps: string; load: string; rpe: string };
export type PlannedSet = { exerciseId: string; name: string; setNo: number; repsMin?: number; repsMax?: number; durationSec?: number; targetRpe?: number; restSec?: number };
export type BuildResult = { ok: true; body: SetLogRequest } | { ok: false; errors: Record<string, string> };

function num(raw: string): number | undefined {
  const s = normalizeDigits(raw.trim()).replace(/[٫,]/g, ".");
  if (s === "" || !/^\d+(\.\d+)?$/.test(s)) return undefined;
  return Number(s);
}

/** Time-based sets (duration only) need no reps; otherwise reps 1..200, load 0..1000 kg (blank = bodyweight = 0), RPE 1..10 optional. */
export function buildSetLog(p: PlannedSet, d: SetDraft, uuid: string): BuildResult {
  const errors: Record<string, string> = {};
  const timeBased = p.durationSec !== undefined && p.repsMin === undefined;
  const reps = num(d.reps);
  if (!timeBased && (reps === undefined || !Number.isInteger(reps) || reps < 1 || reps > 200)) errors.reps = "reps";
  const load = d.load.trim() === "" ? 0 : num(d.load);
  if (load === undefined || load < 0 || load > 1000) errors.load = "load";
  const rpe = d.rpe.trim() === "" ? undefined : num(d.rpe);
  if (d.rpe.trim() !== "" && (rpe === undefined || rpe < 1 || rpe > 10)) errors.rpe = "rpe";
  if (Object.keys(errors).length) return { ok: false, errors };
  const body: SetLogRequest = { client_uuid: uuid, exercise_id: p.exerciseId, set_no: p.setNo, load_kg: load as number };
  if (timeBased) body.duration_sec = p.durationSec; else body.reps = reps;
  if (rpe !== undefined) body.rpe = rpe;
  return { ok: true, body };
}

export function skipSetLog(p: PlannedSet, uuid: string): SetLogRequest {
  return { client_uuid: uuid, exercise_id: p.exerciseId, set_no: p.setNo, skipped: true, skipped_reason: "skipped_by_user" };
}

export function plannedSets(day: WorkoutDay): PlannedSet[] {
  const out: PlannedSet[] = [];
  for (const e of day.exercises ?? []) {
    if (!e.exercise_id || e.role === "warmup" || e.role === "cooldown") continue;       // warm-up/cool-down are guidance, not logged work
    for (const s of e.sets ?? []) out.push({ exerciseId: e.exercise_id, name: e.name ?? "", setNo: s.set_no ?? out.length + 1, repsMin: s.reps_min, repsMax: s.reps_max,
      durationSec: s.duration_sec, targetRpe: s.target_rpe, restSec: s.rest_sec });
  }
  return out;
}

export function isLogged(session: Pick<WorkoutSession, "logged_sets"> | undefined, p: PlannedSet): boolean {
  return (session?.logged_sets ?? []).some((l) => l.exercise_id === p.exerciseId && l.set_no === p.setNo);
}

export function progress(session: WorkoutSession | undefined, sets: PlannedSet[]): { done: number; total: number } {
  return { done: sets.filter((s) => isLogged(session, s)).length, total: sets.length };
}

export function nextSet(session: WorkoutSession | undefined, sets: PlannedSet[]): PlannedSet | undefined {
  return sets.find((s) => !isLogged(session, s));
}

export const PAIN_REGIONS = ["neck", "shoulder", "elbow", "wrist_hand", "upper_back", "lower_back", "hip", "knee", "ankle_foot", "chest", "other"] as const;

export function finishRequest(o: { difficulty?: string; stoppedForPain?: boolean; painRegion?: string; notes?: string }): SessionFinishRequest {
  const body: SessionFinishRequest = {};
  const d = o.difficulty ? num(o.difficulty) : undefined;
  if (d !== undefined && Number.isInteger(d) && d >= 1 && d <= 10) body.perceived_difficulty = d;
  if (o.stoppedForPain) {
    body.aborted_reason = "pain";
    if (o.painRegion && (PAIN_REGIONS as readonly string[]).includes(o.painRegion)) body.pain_region = o.painRegion as NonNullable<SessionFinishRequest["pain_region"]>;
  }
  if (o.notes && o.notes.trim()) body.notes = o.notes.trim().slice(0, 1000);
  return body;
}

export function newUuid(): string {
  const c = globalThis.crypto as Crypto | undefined;
  if (c?.randomUUID) return c.randomUUID();
  const b = new Uint8Array(16); (c ?? { getRandomValues: (a: Uint8Array) => a.map(() => Math.floor(Math.random() * 256)) }).getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40; b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

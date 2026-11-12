// Client-side aggregation of the user's own logged sessions (no invented data): weekly volume and session counts.
import type { WorkoutSession } from "./api/generated.ts";

export interface WeekBucket { weekStart: string; sessions: number; volumeKg: number; sets: number }

function mondayOf(d: Date): Date {
  const x = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  x.setUTCDate(x.getUTCDate() - ((x.getUTCDay() + 6) % 7));
  return x;
}
const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Last `weeks` calendar weeks (Monday-based, UTC), oldest first, empty weeks included so gaps are visible. In-progress sessions are ignored. */
export function weeklyBuckets(sessions: readonly WorkoutSession[], now: Date, weeks = 8): WeekBucket[] {
  const end = mondayOf(now);
  const buckets: WeekBucket[] = [];
  for (let i = weeks - 1; i >= 0; i--) {
    const d = new Date(end); d.setUTCDate(d.getUTCDate() - 7 * i);
    buckets.push({ weekStart: iso(d), sessions: 0, volumeKg: 0, sets: 0 });
  }
  const byKey = new Map(buckets.map((b) => [b.weekStart, b]));
  for (const s of sessions) {
    if (!s.started_at || s.status === "in_progress") continue;
    const t = new Date(s.started_at);
    if (Number.isNaN(t.getTime())) continue;
    const b = byKey.get(iso(mondayOf(t)));
    if (!b) continue;
    b.sessions += 1; b.volumeKg += s.volume_kg ?? 0; b.sets += s.sets_done ?? 0;
  }
  return buckets;
}

/** Bar height in percent; never below a visible sliver for non-zero values, 0 for zero. */
export function barPct(value: number, max: number): number {
  if (!(value > 0) || !(max > 0)) return 0;
  return Math.max(4, Math.min(100, Math.round((value / max) * 100)));
}

/** The `n` calendar dates (YYYY-MM-DD, UTC) ending at `end`, oldest first. */
export function lastDates(end: string, n: number): string[] {
  const base = new Date(`${end}T00:00:00Z`);
  if (Number.isNaN(base.getTime()) || n < 1) return [];
  return Array.from({ length: n }, (_, i) => { const d = new Date(base); d.setUTCDate(d.getUTCDate() - (n - 1 - i)); return iso(d); });
}

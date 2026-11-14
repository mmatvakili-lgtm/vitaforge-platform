// Presentation helpers for the analytics view (numbers come from the server; nothing is invented here).

/** SVG polyline points for a series with gaps (null). Returns one point list per contiguous run so gaps stay visible. */
export function sparkRuns(series: readonly (number | null)[], w: number, h: number, pad = 3): string[] {
  const vals = series.filter((v): v is number => v !== null);
  if (vals.length === 0) return [];
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const span = hi - lo || 1;
  const step = series.length > 1 ? (w - 2 * pad) / (series.length - 1) : 0;
  const runs: string[] = [];
  let cur: string[] = [];
  series.forEach((v, i) => {
    if (v === null) { if (cur.length) runs.push(cur.join(" ")); cur = []; return; }
    const x = pad + i * step;
    const y = hi === lo ? h / 2 : h - pad - ((v - lo) / span) * (h - 2 * pad);
    cur.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  });
  if (cur.length) runs.push(cur.join(" "));
  return runs;
}

export const INSIGHT_KEYS = ["insufficient_data", "volume_drop", "e1rm_up", "muscle_low", "muscle_high", "rpe_high", "inactive", "records"] as const;
export type InsightKey = (typeof INSIGHT_KEYS)[number];

/** Message key for an insight; unknown keys (newer server) fall back to a neutral text instead of raw output. */
export function insightMessageKey(key: string): string {
  return (INSIGHT_KEYS as readonly string[]).includes(key) ? `analytics.insight.${key}` : "analytics.insight.unknown";
}

/** Only scalar params are interpolated; objects/arrays are dropped. */
export function insightParams(p: Record<string, unknown>): Record<string, string | number> {
  const out: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(p)) if (typeof v === "string" || typeof v === "number") out[k] = v;
  return out;
}

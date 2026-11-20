/** Pure helpers for the admin dashboard (no DOM, unit-tested). */
export interface DayCount { day: number; count: number }

/** Bar heights as 0..1 relative to the largest value; an all-zero series stays flat (never NaN). */
export function barHeights(series: DayCount[]): number[] {
  const max = Math.max(0, ...series.map((d) => d.count));
  return series.map((d) => (max === 0 ? 0 : d.count / max));
}
export const sumCounts = (series: DayCount[]): number => series.reduce((a, d) => a + d.count, 0);

export function fmtBytes(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "0 B";
  if (n < 1024) return `${Math.round(n)} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

/** Share in percent, rounded; 0 when the whole is 0. */
export function pct(part: number, whole: number): number {
  return whole > 0 ? Math.round((part / whole) * 100) : 0;
}

export interface AuditEntry { at: number; actor: string; action: string; target: string; before: unknown; after: unknown }
/** Groups newest-first audit entries by UTC day, keeping order. */
export function groupAuditByDay(entries: AuditEntry[]): { day: number; items: AuditEntry[] }[] {
  const out: { day: number; items: AuditEntry[] }[] = [];
  for (const e of entries) {
    const d = Math.floor(e.at / 86400) * 86400;
    const last = out[out.length - 1];
    if (last && last.day === d) last.items.push(e); else out.push({ day: d, items: [e] });
  }
  return out;
}

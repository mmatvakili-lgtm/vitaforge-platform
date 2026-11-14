// Body-measurement metrics. Ranges mirror the server (backend/app_services/extras.py METRICS); the server stays authoritative.
export const BODY_METRICS = {
  height: { unit: "cm", min: 80, max: 250 }, weight: { unit: "kg", min: 20, max: 400 }, waist: { unit: "cm", min: 20, max: 300 },
  abdomen: { unit: "cm", min: 20, max: 300 }, chest: { unit: "cm", min: 20, max: 300 }, arm: { unit: "cm", min: 5, max: 100 },
  forearm: { unit: "cm", min: 5, max: 100 }, thigh: { unit: "cm", min: 10, max: 200 }, calf: { unit: "cm", min: 10, max: 100 },
  body_fat_pct: { unit: "%", min: 1, max: 80 }, lean_mass: { unit: "kg", min: 5, max: 300 },
} as const;
export type BodyMetric = keyof typeof BODY_METRICS;
export const BODY_METRIC_KEYS = Object.keys(BODY_METRICS) as BodyMetric[];

/** Parses user input (Latin, Persian or Arabic-Indic digits; "," or "٫" as decimal separator). Returns null when not a finite in-range number. */
export function parseMeasurement(metric: BodyMetric, raw: string): number | null {
  const norm = raw.trim()
    .replace(/[۰-۹]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/[,٫]/g, ".");
  if (!/^\d+(\.\d+)?$/.test(norm)) return null;
  const v = Number(norm);
  const s = BODY_METRICS[metric];
  return Number.isFinite(v) && v >= s.min && v <= s.max ? v : null;
}

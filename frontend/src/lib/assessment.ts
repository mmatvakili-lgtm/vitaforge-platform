// Movement self-assessment: form model + parsing (pure, no React). The server (assessment/engine.py) stays authoritative.
import { normalizeDigits } from "./i18n.ts";
import type { AssessmentRequest } from "./api/generated.ts";

export type Answers = AssessmentRequest["answers"];
export type FieldSpec =
  | { key: string; kind: "int"; min: number; max: number; unit?: "reps" | "sec" | "cm" | "min" }
  | { key: string; kind: "enum"; options: readonly string[] }
  | { key: string; kind: "bool" };
export type StepSpec = { id: string; fields: readonly FieldSpec[] };

export const STEPS: readonly StepSpec[] = [
  { id: "legs", fields: [{ key: "squat_reps", kind: "int", min: 0, max: 100, unit: "reps" }, { key: "squat_heels_down", kind: "bool" }, { key: "squat_knees_cave", kind: "bool" }] },
  { id: "hinge", fields: [{ key: "hinge_reach", kind: "enum", options: ["above_knee", "shin", "toes", "palms_floor"] }, { key: "glute_bridge_s", kind: "int", min: 0, max: 180, unit: "sec" }] },
  { id: "push", fields: [{ key: "push_variant", kind: "enum", options: ["wall", "incline", "knee", "standard"] }, { key: "push_reps", kind: "int", min: 0, max: 100, unit: "reps" }] },
  { id: "pull", fields: [{ key: "pull_variant", kind: "enum", options: ["none", "inverted_row", "band_assisted", "pullup"] }, { key: "pull_reps", kind: "int", min: 0, max: 50, unit: "reps" }] },
  { id: "core", fields: [{ key: "plank_s", kind: "int", min: 0, max: 300, unit: "sec" }, { key: "side_plank_left_s", kind: "int", min: 0, max: 180, unit: "sec" }, { key: "side_plank_right_s", kind: "int", min: 0, max: 180, unit: "sec" }] },
  { id: "balance", fields: [{ key: "balance_left_s", kind: "int", min: 0, max: 60, unit: "sec" }, { key: "balance_right_s", kind: "int", min: 0, max: 60, unit: "sec" }] },
  { id: "mobility", fields: [{ key: "overhead_reach", kind: "enum", options: ["no", "partial", "yes"] }, { key: "ankle_knee_to_wall_cm", kind: "int", min: 0, max: 20, unit: "cm" }, { key: "cardio_minutes", kind: "int", min: 0, max: 60, unit: "min" }] },
] as const;

export type Draft = Record<string, string>;      // blank = skipped; bool fields use "yes" | "no"
export type BuildResult = { ok: true; answers: Answers } | { ok: false; errors: Record<string, string> };

/** Builds the request body from the raw form. Blank fields are skipped; invalid ones are reported per field. At least one field is required. */
export function buildAnswers(draft: Draft, painRegions: readonly string[] = []): BuildResult {
  const errors: Record<string, string> = {};
  const out: Record<string, unknown> = {};
  for (const step of STEPS) {
    for (const f of step.fields) {
      const raw = (draft[f.key] ?? "").trim();
      if (raw === "") continue;
      if (f.kind === "int") {
        const s = normalizeDigits(raw);
        const v = /^\d+$/.test(s) ? Number(s) : NaN;
        if (!Number.isInteger(v) || v < f.min || v > f.max) errors[f.key] = "range";
        else out[f.key] = v;
      } else if (f.kind === "enum") {
        if (!f.options.includes(raw)) errors[f.key] = "enum"; else out[f.key] = raw;
      } else if (raw === "yes" || raw === "no") out[f.key] = raw === "yes";
      else errors[f.key] = "bool";
    }
  }
  if (Object.keys(errors).length) return { ok: false, errors };
  if (Object.keys(out).length === 0) return { ok: false, errors: { _form: "empty" } };
  if (painRegions.length) out.pain_regions = [...new Set(painRegions)];
  return { ok: true, answers: out as Answers };
}

export type Domain = { score: number | null; band: string | null; level: string | null; tested: boolean; caution: boolean };
export type Profile = {
  method: string; content_status: "ai_curated"; domains: Record<string, Domain>; overall_level: string | null; tested_count: number;
  strengths: { domain: string; score: number }[]; weaknesses: { domain: string; score: number }[];
  flags: { key: string; weaker_side?: string; gap_pct?: number; lagging?: string; gap?: number }[];
  limiters: string[]; corrective_focus: string[]; priorities: Record<string, number>; pain_reported: boolean; pain_regions: string[]; untested: string[];
};
export const DOMAIN_ORDER = ["legs", "hinge", "push", "pull", "core", "balance", "mobility", "cardio"] as const;

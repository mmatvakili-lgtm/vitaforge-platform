// Mirrors the server rules (app_services/health_profile.py). The server stays the authority; this only avoids needless round trips.
export const GOALS = ["strength", "muscle_gain", "general_fitness", "fat_loss"] as const;
export const LEVELS = ["beginner", "intermediate", "advanced"] as const;
export const EQUIPMENT = ["dumbbell", "barbell", "bench", "box", "band", "machine", "kettlebell", "pull_up_bar", "cable"] as const;
/** Screening v1 has no endpoint listing its questions (API_GAPS), so the ids are fixed here and covered by a test against the Safety Core catalog. */
export const SCREENING_VERSION = 1;
export const SCREENING_QUESTIONS = ["chest_pain", "fainting", "severe_unexplained_pain", "neurological_symptoms"] as const;

export type Goal = (typeof GOALS)[number];
export type Level = (typeof LEVELS)[number];

/** Server-side step numbers (ONBOARDING_STEPS in the adapter): steps 5..14 are not built yet. */
export const STEP_NUMBER = { basics: 1, goal: 2, schedule: 3, equipment: 4 } as const;
export type StepName = keyof typeof STEP_NUMBER;

export type FieldErrors = Record<string, string>;
const int = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);

export function validateBasics(a: { age?: unknown }): FieldErrors {
  return int(a.age) && a.age > 0 && a.age < 120 ? {} : { age: "age" };
}
export function validateGoal(a: { goal?: unknown; level?: unknown }): FieldErrors {
  const e: FieldErrors = {};
  if (!GOALS.includes(a.goal as Goal)) e.goal = "goal";
  if (!LEVELS.includes(a.level as Level)) e.level = "level";
  return e;
}
export function validateSchedule(a: { days_per_week?: unknown; session_minutes?: unknown }): FieldErrors {
  const e: FieldErrors = {};
  if (!int(a.days_per_week) || a.days_per_week < 1 || a.days_per_week > 6) e.days_per_week = "days";
  if (!int(a.session_minutes) || a.session_minutes < 20 || a.session_minutes > 180) e.session_minutes = "minutes";
  return e;
}
export function validateEquipment(a: { equipment?: unknown }): FieldErrors {
  return Array.isArray(a.equipment) && a.equipment.every((x) => EQUIPMENT.includes(x)) ? {} : { equipment: "equipment" };
}

export function parseIntField(raw: string): number | undefined {
  const s = raw.trim();
  return /^\d+$/.test(s) ? Number(s) : undefined;
}

/** Where to resume: server current_step is authoritative when onboarding is not complete; consent and screening follow the 4 data steps. */
export type WizardStage = "basics" | "goal" | "schedule" | "equipment" | "consent" | "screening" | "finish";
export function resumeStage(o: { status?: string; current_step?: number; summary_ready?: boolean; safety_screening_complete?: boolean } | undefined, consentGranted: boolean): WizardStage {
  if (!o) return "basics";
  if (!o.summary_ready) return (["basics", "goal", "schedule", "equipment"] as const)[Math.min(Math.max((o.current_step ?? 1) - 1, 0), 3)];
  if (!consentGranted) return "consent";
  if (!o.safety_screening_complete) return "screening";
  return "finish";
}

export function allScreeningAnswered(a: Record<string, boolean | undefined>): boolean {
  return SCREENING_QUESTIONS.every((q) => typeof a[q] === "boolean");
}

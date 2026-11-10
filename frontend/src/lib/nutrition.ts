import { t, type Locale } from "./i18n.ts";
import type { MealPlanResponse, NutritionEstimate, NutritionProfileRequest } from "./api/generated.ts";

export const ACTIVITY = ["sedentary", "light", "moderate", "active", "very_active"] as const;
export const ALLERGENS = ["milk", "egg", "fish", "shellfish", "tree_nut", "peanut", "wheat", "soy", "sesame"] as const;
export const DIET_TAGS = ["vegetarian", "vegan", "halal", "gluten_free", "lactose_free"] as const;
export const SCREEN_KEYS = ["eating_disorder_risk", "medical_diet_needed", "pregnant_or_lactating"] as const;
export const SLOTS = ["breakfast", "lunch", "dinner", "snack"] as const;
export const NUTRIENT_ORDER = ["kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg", "calcium_mg", "iron_mg", "potassium_mg", "vitamin_c_mg"] as const;

/** The only gate for showing meals: status OK with at least one day. Everything else is an explanation, never a plan. */
export type MealView =
  | { kind: "plan"; res: MealPlanResponse }
  | { kind: "needs_content" }
  | { kind: "needs_info"; reasons: string[] }
  | { kind: "referred"; status: "REFER" | "BLOCKED"; reasons: string[] }
  | { kind: "unavailable" };

export function mealView(res: MealPlanResponse | undefined): MealView {
  if (!res) return { kind: "unavailable" };
  switch (res.status) {
    case "OK": return Array.isArray(res.days) && res.days.length > 0 ? { kind: "plan", res } : { kind: "needs_content" };
    case "NEEDS_CONTENT": return { kind: "needs_content" };
    case "NEEDS_INFO": return { kind: "needs_info", reasons: res.reasons ?? [] };
    case "REFER": case "BLOCKED": return { kind: "referred", status: res.status, reasons: res.reasons ?? [] };
    default: return { kind: "unavailable" };
  }
}

export type BudgetState = "none" | "met" | "exceeded" | "unverifiable";
export function budgetState(res: MealPlanResponse, requestedBudget: boolean): BudgetState {
  if (!requestedBudget) return "none";
  if (res.budget_met === true) return "met";
  if (res.budget_met === false) return "exceeded";
  return "unverifiable";           // missing or stale prices: never presented as met or exceeded
}

export type NutrientLine = { key: string; value: number };
/** Only nutrients actually present are listed, in a fixed order; absent ones are never shown as 0. */
export function nutrientLines(n: Record<string, unknown> | undefined): NutrientLine[] {
  const out: NutrientLine[] = [];
  for (const key of NUTRIENT_ORDER) {
    const v = n?.[key];
    if (typeof v === "number" && Number.isFinite(v)) out.push({ key, value: v });
  }
  return out;
}

export function rangeText(r: unknown): [number, number] | undefined {
  return Array.isArray(r) && r.length >= 2 && typeof r[0] === "number" && typeof r[1] === "number" ? [r[0], r[1]] : undefined;
}

export function macroRanges(e: NutritionEstimate | undefined): Record<string, [number, number]> {
  const out: Record<string, [number, number]> = {};
  for (const [k, v] of Object.entries((e?.macros ?? {}) as Record<string, unknown>)) {
    const r = rangeText(v);
    if (r) out[k] = r;
  }
  return out;
}

export type FieldErrors = Record<string, string>;
export function validateProfile(p: { height_cm?: number; weight_kg?: number; activity?: string; screening: Partial<Record<(typeof SCREEN_KEYS)[number], boolean>> }): FieldErrors {
  const e: FieldErrors = {};
  if (!(typeof p.height_cm === "number" && p.height_cm >= 100 && p.height_cm <= 250)) e.height_cm = "height";
  if (!(typeof p.weight_kg === "number" && p.weight_kg >= 25 && p.weight_kg <= 400)) e.weight_kg = "weight";
  if (!ACTIVITY.includes(p.activity as (typeof ACTIVITY)[number])) e.activity = "activity";
  if (!SCREEN_KEYS.every((k) => typeof p.screening[k] === "boolean")) e.screening = "screening";
  return e;
}

export function buildProfileRequest(p: { sex?: string; height_cm: number; weight_kg: number; activity: string; screening: Record<string, boolean> }): NutritionProfileRequest {
  return { ...(p.sex === "male" || p.sex === "female" ? { sex: p.sex } : {}), height_cm: p.height_cm, weight_kg: p.weight_kg,
    activity: p.activity as NutritionProfileRequest["activity"], goal: "maintain", screening: p.screening as NutritionProfileRequest["screening"] };
}

export function validateMealRequest(r: { budget?: string; currency?: string; region?: string; maxCook?: string }): FieldErrors {
  const e: FieldErrors = {};
  const b = r.budget?.trim();
  if (b) {
    if (!(Number(b) > 0)) e.weekly_budget = "budget";
    if (!/^[A-Z]{3}$/.test(r.currency?.trim() ?? "")) e.currency = "currency";
    if (!((r.region?.trim().length ?? 0) >= 2)) e.region = "region";
  }
  const m = r.maxCook?.trim();
  if (m && !(/^\d+$/.test(m) && Number(m) >= 5 && Number(m) <= 240)) e.max_cook_minutes = "cook";
  return e;
}

/** Locale-aware weekday/day labels; Persian uses the Persian calendar and digits, English the Gregorian. */
export function dayLabel(iso: string, locale: "fa" | "en"): { weekday: string; day: string } {
  const d = new Date(`${iso}T12:00:00Z`);
  const tag = locale === "fa" ? "fa-IR-u-ca-persian" : "en-US";
  return {
    weekday: new Intl.DateTimeFormat(tag, { weekday: "short", timeZone: "UTC" }).format(d),
    day: new Intl.DateTimeFormat(tag, { day: "numeric", month: "short", timeZone: "UTC" }).format(d),
  };
}

export function totalGrams(res: MealPlanResponse): number {
  return (res.shopping ?? []).reduce((a, s) => a + (s.grams ?? 0), 0);
}

/** Localised text for a planner reason code; unknown codes are shown as the code so nothing is silently hidden. */
export function reasonText(locale: Locale, code: string): string {
  const [base, arg] = code.split(":");
  if (base === "NUT-NO-RECIPE") return t(locale, "nut.reason.NUT-NO-RECIPE", { slot: t(locale, `nut.slot.${arg}`) });
  const key = `nut.reason.${code}`;
  const msg = t(locale, key);
  return msg === key ? t(locale, "nut.reason.unknown", { code }) : msg;
}

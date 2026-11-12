// Pure helpers for the food browser, the daily log, prices and the shopping list. No I/O: pages call the typed client.
import { normalizeDigits } from "./i18n.ts";
import type { MealEntry, MealLogRequest, ProgressionItem, UserPriceRequest } from "./api/generated.ts";

export const MEAL_SLOTS = ["breakfast", "lunch", "dinner", "snack"] as const;
export type Slot = (typeof MEAL_SLOTS)[number];
export const SHOPPING_MAX = 300;

export function defaultSlot(hour: number): Slot {
  if (hour >= 5 && hour < 11) return "breakfast";
  if (hour >= 11 && hour < 16) return "lunch";
  if (hour >= 16 && hour < 22) return "dinner";
  return "snack";
}

/** A positive finite number from user text (Persian digits accepted); anything else is undefined, never 0. */
export function parsePositive(raw: string): number | undefined {
  const v = Number(normalizeDigits(raw.trim()).replace(/٫/g, "."));
  return Number.isFinite(v) && v > 0 ? v : undefined;
}

export type MealSource =
  | { kind: "food"; id: string; grams: string }
  | { kind: "recipe"; id: string; servings: string }
  | { kind: "manual"; name: string; kcal: string; protein_g: string; carbs_g: string; fat_g: string };

/** Exactly one source per request; returns null when the input is not valid so nothing partial is sent. */
export function buildMealRequest(slot: Slot, src: MealSource): MealLogRequest | null {
  if (src.kind === "food") { const g = parsePositive(src.grams); return g ? { slot, food_id: src.id, grams: g } : null; }
  if (src.kind === "recipe") { const s = parsePositive(src.servings); return s ? { slot, recipe_id: src.id, servings: s } : null; }
  const name = src.name.trim(); const kcal = parsePositive(src.kcal);
  if (!name || !kcal) return null;
  const req: MealLogRequest = { slot, name, kcal };
  for (const k of ["protein_g", "carbs_g", "fat_g"] as const) {
    const raw = src[k].trim();
    if (raw) { const v = Number(normalizeDigits(raw)); if (!Number.isFinite(v) || v < 0) return null; req[k] = v; }
  }
  return req;
}

export type AlertKind = "allergen" | "unknown" | null;
export function alertKind(e: Pick<MealEntry, "allergen_alert">): AlertKind {
  const a = e.allergen_alert as { allergens?: string[]; unknown?: boolean } | null | undefined;
  if (!a || typeof a !== "object") return null;
  if ((a.allergens ?? []).length > 0) return "allergen";
  return a.unknown ? "unknown" : null;
}

export function groupBySlot(meals: MealEntry[]): Array<{ slot: Slot; meals: MealEntry[] }> {
  return MEAL_SLOTS.map((slot) => ({ slot, meals: meals.filter((m) => m.slot === slot) })).filter((g) => g.meals.length > 0);
}

export function validatePrice(p: { food_id: string; price: string; currency: string; region: string }): UserPriceRequest | null {
  const price = parsePositive(p.price);
  const currency = p.currency.trim().toUpperCase(); const region = p.region.trim();
  if (!p.food_id || !price || !/^[A-Z]{3}$/.test(currency) || !/^[A-Za-z0-9-]{2,16}$/.test(region)) return null;
  return { food_id: p.food_id, price_per_kg: price, currency, region };
}

export function toggleChecked(list: readonly string[], id: string): string[] {
  if (list.includes(id)) return list.filter((x) => x !== id);
  return list.length >= SHOPPING_MAX ? [...list] : [...list, id];
}
/** Persisted ticks for items that are no longer on the list are dropped so the saved state never grows stale. */
export function pruneChecked(list: readonly string[], currentIds: readonly string[]): string[] {
  const keep = new Set(currentIds);
  return list.filter((x) => keep.has(x));
}

export type ProgressTone = "up" | "hold" | "down" | "stop" | "info";
export function progressionTone(a: ProgressionItem["action"]): ProgressTone {
  switch (a) {
    case "increase_load": case "increase_reps": return "up";
    case "hold": return "hold";
    case "reduce_load": case "suggest_deload": return "down";
    case "pause_pain": case "locked": return "stop";
    default: return "info";
  }
}

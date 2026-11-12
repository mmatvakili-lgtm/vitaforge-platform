import assert from "node:assert/strict";
import { test } from "node:test";
import { alertKind, buildMealRequest, defaultSlot, groupBySlot, parsePositive, progressionTone, pruneChecked, toggleChecked, validatePrice, SHOPPING_MAX } from "./nutrition-log.ts";
import type { MealEntry } from "./api/generated.ts";

test("default slot follows the hour", () => {
  assert.deepEqual([6, 12, 19, 2].map(defaultSlot), ["breakfast", "lunch", "dinner", "snack"]);
});
test("parsePositive accepts Persian digits and rejects zero/garbage", () => {
  assert.equal(parsePositive("۱۵۰"), 150);
  assert.equal(parsePositive("0"), undefined);
  assert.equal(parsePositive("abc"), undefined);
  assert.equal(parsePositive("-3"), undefined);
});
test("meal requests carry exactly one source and reject invalid input", () => {
  assert.deepEqual(buildMealRequest("lunch", { kind: "food", id: "f", grams: "150" }), { slot: "lunch", food_id: "f", grams: 150 });
  assert.deepEqual(buildMealRequest("dinner", { kind: "recipe", id: "r", servings: "1.5" }), { slot: "dinner", recipe_id: "r", servings: 1.5 });
  assert.equal(buildMealRequest("lunch", { kind: "food", id: "f", grams: "0" }), null);
  assert.equal(buildMealRequest("snack", { kind: "manual", name: "", kcal: "100", protein_g: "", carbs_g: "", fat_g: "" }), null);
  assert.deepEqual(buildMealRequest("snack", { kind: "manual", name: "Bar", kcal: "200", protein_g: "10", carbs_g: "", fat_g: "" }), { slot: "snack", name: "Bar", kcal: 200, protein_g: 10 });
  assert.equal(buildMealRequest("snack", { kind: "manual", name: "Bar", kcal: "200", protein_g: "-1", carbs_g: "", fat_g: "" }), null);
});
test("allergen alerts: known allergen vs unknown data vs none", () => {
  assert.equal(alertKind({ allergen_alert: { allergens: ["milk"] } }), "allergen");
  assert.equal(alertKind({ allergen_alert: { unknown: true } }), "unknown");
  assert.equal(alertKind({ allergen_alert: null }), null);
});
test("meals group by slot in a fixed order and skip empty slots", () => {
  const m = (slot: string) => ({ id: slot, slot } as unknown as MealEntry);
  assert.deepEqual(groupBySlot([m("dinner"), m("breakfast")]).map((g) => g.slot), ["breakfast", "dinner"]);
});
test("price validation", () => {
  assert.deepEqual(validatePrice({ food_id: "f", price: "۱۰۰", currency: "irr", region: "IR-ISF" }), { food_id: "f", price_per_kg: 100, currency: "IRR", region: "IR-ISF" });
  assert.equal(validatePrice({ food_id: "f", price: "10", currency: "TOMAN", region: "IR" }), null);
  assert.equal(validatePrice({ food_id: "f", price: "10", currency: "USD", region: "x" }), null);
});
test("shopping ticks toggle, are capped and pruned", () => {
  assert.deepEqual(toggleChecked(["a"], "b"), ["a", "b"]);
  assert.deepEqual(toggleChecked(["a", "b"], "a"), ["b"]);
  const full = Array.from({ length: SHOPPING_MAX }, (_, i) => String(i));
  assert.equal(toggleChecked(full, "new").length, SHOPPING_MAX);
  assert.deepEqual(pruneChecked(["a", "b"], ["b", "c"]), ["b"]);
});
test("progression tone never presents pain or locks as progress", () => {
  assert.equal(progressionTone("pause_pain"), "stop");
  assert.equal(progressionTone("locked"), "stop");
  assert.equal(progressionTone("increase_load"), "up");
  assert.equal(progressionTone("insufficient_data"), "info");
});

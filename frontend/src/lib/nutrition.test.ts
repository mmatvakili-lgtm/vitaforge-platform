import { test } from "node:test";
import assert from "node:assert/strict";
import { reasonText, budgetState, dayLabel, macroRanges, mealView, nutrientLines, validateMealRequest, validateProfile } from "./nutrition.ts";
import { ALLERGENS, DIET_TAGS } from "./nutrition.ts";
import { messageKeys, t } from "./i18n.ts";
import type { MealPlanResponse } from "./api/generated.ts";

const base = (o: Partial<MealPlanResponse>): MealPlanResponse => ({ status: "OK", reasons: [], days: [], shopping: [], labels: [], ...o });
const day = { index: 0, date: "2026-11-10", meals: [], kcal: 2000, protein_g: 80 };

test("a plan is shown only for OK with days", () => {
  assert.equal(mealView(base({ status: "OK", days: [day] })).kind, "plan");
  assert.equal(mealView(base({ status: "OK", days: [] })).kind, "needs_content");
  assert.equal(mealView(base({ status: "NEEDS_CONTENT" })).kind, "needs_content");
  assert.equal(mealView(undefined).kind, "unavailable");
});

test("days are never rendered for any non-OK status even if the server sent them", () => {
  for (const s of ["NEEDS_CONTENT", "NEEDS_INFO", "BLOCKED", "REFER"] as const) assert.notEqual(mealView(base({ status: s, days: [day] })).kind, "plan", s);
  assert.equal(mealView(base({ status: "REFER", days: [day] })).kind, "referred");
});

test("budget state never claims met/exceeded without verified prices", () => {
  assert.equal(budgetState(base({ budget_met: null }), true), "unverifiable");
  assert.equal(budgetState(base({ budget_met: true }), true), "met");
  assert.equal(budgetState(base({ budget_met: false }), true), "exceeded");
  assert.equal(budgetState(base({ budget_met: true }), false), "none");
});

test("absent nutrients are omitted, not zero-filled", () => {
  assert.deepEqual(nutrientLines({ protein_g: 10, kcal: 100 }).map((l) => l.key), ["kcal", "protein_g"]);
  assert.deepEqual(nutrientLines(undefined), []);
  assert.deepEqual(macroRanges({ status: "OK", labels: [], macros: { protein_g: [80, 140], bad: "x" } }), { protein_g: [80, 140] });
});

test("validators", () => {
  const sc = { eating_disorder_risk: false, medical_diet_needed: false, pregnant_or_lactating: false };
  assert.deepEqual(validateProfile({ height_cm: 175, weight_kg: 70, activity: "moderate", screening: sc }), {});
  assert.deepEqual(Object.keys(validateProfile({ height_cm: 20, weight_kg: 5, activity: "x", screening: {} })).sort(), ["activity", "height_cm", "screening", "weight_kg"]);
  assert.deepEqual(validateMealRequest({}), {});
  assert.deepEqual(Object.keys(validateMealRequest({ budget: "100" })).sort(), ["currency", "region"]);
  assert.deepEqual(validateMealRequest({ budget: "100", currency: "IRR", region: "IR-ISF", maxCook: "30" }), {});
  assert.ok(validateMealRequest({ maxCook: "2" }).max_cook_minutes);
});

test("day labels follow the locale calendar", () => {
  assert.notEqual(dayLabel("2026-11-10", "fa").day, dayLabel("2026-11-10", "en").day);
  assert.match(dayLabel("2026-11-10", "en").day, /Nov/);
});

test("every allergen and diet tag has labels in both languages", () => {
  for (const l of ["fa", "en"] as const) {
    for (const a of ALLERGENS) assert.notEqual(t(l, `allergen.${a}`), `allergen.${a}`, `${l}:${a}`);
    for (const d of DIET_TAGS) assert.notEqual(t(l, `diet.${d}`), `diet.${d}`, `${l}:${d}`);
  }
  assert.deepEqual(messageKeys("fa").sort(), messageKeys("en").sort());
});

test("reason codes map to text in both languages; unknown codes stay visible", () => {
  for (const l of ["fa", "en"] as const) {
    assert.notEqual(reasonText(l, "NUT-PRICE-MISSING"), "nut.reason.NUT-PRICE-MISSING");
    assert.ok(reasonText(l, "NUT-NO-RECIPE:lunch").length > 10);
    assert.ok(reasonText(l, "NUT-SOMETHING-NEW").includes("NUT-SOMETHING-NEW"));
  }
});

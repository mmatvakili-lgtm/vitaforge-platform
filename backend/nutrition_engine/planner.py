"""Weekly meal planner (general wellness, maintenance energy only). NOT medical nutrition therapy.

Runs only behind a NutritionResult with status OK (Safety Core gate + screening already applied there). Allergen status that is unknown
excludes a recipe; prices are used only when fresh; nothing is invented: if the data cannot support a plan the result is NEEDS_CONTENT.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .engine import NutritionResult
from .food import FoodRecord, NUTRIENTS, usable_for_planning
from .prices import PriceBook
from .recipes import Recipe, nutrition_per_serving, recipe_allergens, recipe_diet_tags, validate_recipe

DEFAULT_SPLIT = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.30, "snack": 0.10}
FIT_TOLERANCE = 0.30            # a portion must land within 30% of the slot energy target or the recipe is not used for that slot
MAX_USES_PER_WEEK = 3


@dataclass(frozen=True)
class MealPlanRequest:
    today: date
    days: int = 7
    meals: Tuple[str, ...] = ("breakfast", "lunch", "dinner", "snack")
    allergens: Tuple[str, ...] = ()
    excluded_food_ids: Tuple[str, ...] = ()
    diet_required: Tuple[str, ...] = ()
    max_cook_minutes: Optional[int] = None
    weekly_budget: Optional[float] = None
    currency: Optional[str] = None
    region: Optional[str] = None
    pantry: Tuple[str, ...] = ()                       # food ids already owned (cost 0)
    allow_unreviewed: bool = False                     # True only for development demos; always labelled


@dataclass(frozen=True)
class PlannedIngredient:
    food_id: str
    name_en: str
    name_fa: Optional[str]
    grams: float                                       # for the planned portion
    allergens: Tuple[str, ...]
    allergens_known: bool


@dataclass(frozen=True)
class PlannedMeal:
    slot: str
    recipe_id: str
    name_en: str
    portion: float                                     # servings (quarter steps)
    kcal: float
    nutrients: Mapping[str, float]
    cook_minutes: int
    cost: Optional[float]                              # None == at least one ingredient has no fresh price
    name_fa: Optional[str] = None
    ingredients: Tuple[PlannedIngredient, ...] = ()
    steps: Tuple[str, ...] = ()
    allergens: Tuple[str, ...] = ()                    # union over ingredients (visibility)
    allergens_known: bool = False
    missing_nutrients: Tuple[str, ...] = ()            # nutrients absent for >=1 ingredient: totals are then lower bounds, never zero-filled



@dataclass(frozen=True)
class MealDay:
    index: int
    date: str
    meals: Tuple[PlannedMeal, ...]
    kcal: float
    protein_g: float
    missing_nutrients: Tuple[str, ...]


@dataclass(frozen=True)
class ShoppingItem:
    food_id: str
    name_en: str
    grams: float
    cost: Optional[float]
    in_pantry: bool


@dataclass(frozen=True)
class MealPlanResult:
    status: str                                        # OK | NEEDS_CONTENT | NEEDS_INFO | BLOCKED | REFER
    reasons: Tuple[str, ...] = ()
    days: Tuple[MealDay, ...] = ()
    shopping: Tuple[ShoppingItem, ...] = ()
    total_cost: Optional[float] = None                 # known-cost part only
    unpriced_food_ids: Tuple[str, ...] = ()
    budget_met: Optional[bool] = None                  # None == no budget given or not verifiable
    labels: Tuple[str, ...] = ("estimate", "not_medical_advice", "maintenance_energy_only")
    target_kcal: Optional[float] = None
    safety_decision_id: Optional[str] = None


def assert_no_fixtures(foods: Mapping[str, FoodRecord], recipes: Sequence[Recipe]) -> None:
    bad = [f.id for f in foods.values() if f.is_test_fixture] + [r.id for r in recipes if r.is_test_fixture]
    if bad:
        raise RuntimeError(f"test fixtures must not be loaded in production: {bad[:3]}")


def _gate(n: NutritionResult) -> Optional[MealPlanResult]:
    if n.status == "OK" and n.tdee:
        return None
    mapped = {"BLOCKED": "BLOCKED", "REFER": "REFER", "NEEDS_INFO": "NEEDS_INFO"}.get(n.status, "BLOCKED")
    return MealPlanResult(mapped, n.reasons, safety_decision_id=n.safety_decision_id)


def plan_week(req: MealPlanRequest, nutrition: NutritionResult, foods: Mapping[str, FoodRecord], recipes: Sequence[Recipe],
              prices: PriceBook = PriceBook()) -> MealPlanResult:
    blocked = _gate(nutrition)
    if blocked:
        return blocked
    if req.weekly_budget is not None and not (req.currency and req.region):
        return MealPlanResult("NEEDS_INFO", ("NUT-BUDGET-NEEDS-CURRENCY-REGION",), safety_decision_id=nutrition.safety_decision_id)
    if not 1 <= req.days <= 7 or not req.meals or any(m not in DEFAULT_SPLIT for m in req.meals):
        return MealPlanResult("NEEDS_INFO", ("NUT-BAD-REQUEST",), safety_decision_id=nutrition.safety_decision_id)

    target = float(nutrition.tdee[1])                                  # maintenance estimate; goal deficits/surpluses are disabled pending expert review
    pn = (nutrition.macros or {}).get("protein_g")
    excl = set(req.excluded_food_ids)
    al = {a.lower() for a in req.allergens}
    need = set(req.diet_required)
    split_total = sum(DEFAULT_SPLIT[m] for m in req.meals)
    split = {m: DEFAULT_SPLIT[m] / split_total for m in req.meals}

    eligible: List[Recipe] = []
    for r in recipes:
        if validate_recipe(r, foods) or r.status == "retired":
            continue
        if r.status != "reviewed" and not req.allow_unreviewed:
            continue
        if not all(usable_for_planning(foods[f], req.allow_unreviewed) for f, _ in r.ingredients):
            continue
        if excl & {f for f, _ in r.ingredients}:
            continue
        if req.max_cook_minutes is not None and r.cook_minutes > req.max_cook_minutes:
            continue
        present, known = recipe_allergens(r, foods)
        if al and (not known or al & {a.lower() for a in present}):
            continue                                                   # unknown allergen status is treated as unsafe
        if need and not need <= recipe_diet_tags(r, foods):
            continue
        eligible.append(r)

    info = {r.id: nutrition_per_serving(r, foods) for r in eligible}
    pantry = set(req.pantry)

    def cost_of(r: Recipe, portion: float) -> Optional[float]:
        if req.weekly_budget is None:
            return None
        total = 0.0
        for fid, g in r.ingredients:
            if fid in pantry:
                continue
            c = prices.cost(fid, g * portion / r.servings, req.region, req.currency, req.today)
            if c is None:
                return None
            total += c
        return total

    def options(slot: str):
        out = []
        for r in eligible:
            if slot not in r.slots:
                continue
            kcal = info[r.id][0].get("kcal")
            if not kcal:
                continue
            portion = min(2.0, max(0.5, round(split[slot] * target / kcal * 4) / 4))
            dev = abs(portion * kcal - split[slot] * target) / (split[slot] * target)
            if dev > FIT_TOLERANCE:
                continue
            out.append((r, portion, dev, cost_of(r, portion)))
        return out

    opts = {m: options(m) for m in req.meals}
    empty = [m for m, o in opts.items() if not o]
    if empty:
        return MealPlanResult("NEEDS_CONTENT", tuple(f"NUT-NO-RECIPE:{m}" for m in empty), target_kcal=target,
                              safety_decision_id=nutrition.safety_decision_id)

    uses: Dict[str, int] = {}
    chosen: List[List[Tuple[str, Recipe, float, float, Optional[float]]]] = []
    for d in range(req.days):
        row = []
        for slot in req.meals:
            recent = {x[1].id for dd in chosen[-2:] for x in dd}
            def score(o):
                r, portion, dev, cost = o
                s = dev + (0.5 if r.id in recent else 0.0) + 0.2 * uses.get(r.id, 0)
                if req.weekly_budget is not None:
                    s += 1.0 if cost is None else 0.0
                    s += (cost / (req.weekly_budget / (req.days * len(req.meals)))) * 0.3 if cost is not None else 0.0
                return (s, r.id)
            pool = [o for o in opts[slot] if uses.get(o[0].id, 0) < MAX_USES_PER_WEEK] or opts[slot]
            r, portion, dev, cost = sorted(pool, key=score)[0]
            uses[r.id] = uses.get(r.id, 0) + 1
            row.append((slot, r, portion, dev, cost))
        chosen.append(row)

    # budget repair: swap the most expensive known-cost meal for a cheaper valid option until within budget or no swap helps
    def known_total():
        return sum(x[4] for dd in chosen for x in dd if x[4] is not None)
    if req.weekly_budget is not None:
        for _ in range(req.days * len(req.meals) * 2):
            if known_total() <= req.weekly_budget:
                break
            best = None
            for di, dd in enumerate(chosen):
                for si, x in enumerate(dd):
                    if x[4] is None:
                        continue
                    cheaper = [o for o in opts[x[0]] if o[3] is not None and o[3] < x[4] - 1e-9 and uses.get(o[0].id, 0) < MAX_USES_PER_WEEK]
                    if cheaper:
                        o = sorted(cheaper, key=lambda o: (o[3], o[2], o[0].id))[0]
                        gain = x[4] - o[3]
                        if best is None or gain > best[0]:
                            best = (gain, di, si, o)
            if best is None:
                break
            _, di, si, o = best
            old = chosen[di][si]
            uses[old[1].id] -= 1
            uses[o[0].id] = uses.get(o[0].id, 0) + 1
            chosen[di][si] = (old[0], o[0], o[1], o[2], o[3])

    days: List[MealDay] = []
    grams: Dict[str, float] = {}
    unpriced: set = set()
    for di, dd in enumerate(chosen):
        meals, tot_k, tot_p, miss = [], 0.0, 0.0, set()
        for slot, r, portion, _dev, cost in dd:
            n, m = info[r.id]
            scaled = {k: v * portion for k, v in n.items()}
            al, known = recipe_allergens(r, foods)
            ings = tuple(PlannedIngredient(fid, foods[fid].name_en, foods[fid].name_fa, round(g * portion / r.servings), tuple(sorted(foods[fid].allergens)),
                                           foods[fid].allergens_known) for fid, g in r.ingredients)
            meals.append(PlannedMeal(slot, r.id, r.name_en, portion, round(scaled.get("kcal", 0.0)), {k: round(v, 1) for k, v in scaled.items()},
                                     r.cook_minutes, None if cost is None else round(cost, 2), r.name_fa, ings, r.steps, tuple(sorted(al)), known, tuple(m)))
            tot_k += scaled.get("kcal", 0.0); tot_p += scaled.get("protein_g", 0.0); miss |= set(m)
            for fid, g in r.ingredients:
                grams[fid] = grams.get(fid, 0.0) + g * portion / r.servings
                if req.weekly_budget is not None and fid not in pantry and prices.fresh(fid, req.region, req.currency, req.today) is None:
                    unpriced.add(fid)
        days.append(MealDay(di, (req.today + timedelta(days=di)).isoformat(), tuple(meals), round(tot_k), round(tot_p, 1), tuple(sorted(miss))))

    shopping = []
    for fid in sorted(grams):
        c = None if req.weekly_budget is None or fid in pantry else prices.cost(fid, grams[fid], req.region, req.currency, req.today)
        shopping.append(ShoppingItem(fid, foods[fid].name_en, round(grams[fid]), None if c is None else round(c, 2), fid in pantry))

    reasons = ["NUT-PLAN-ESTIMATE"]
    labels = ["estimate", "not_medical_advice", "maintenance_energy_only"]
    if nutrition.goal_adjustment != "enabled":
        reasons.append("NUT-R03:goal-targets-disabled")
    used_foods = [foods[f] for r in eligible for f, _ in r.ingredients if r.id in uses]
    if any(f.status != "reviewed" for f in used_foods) or any(r.status != "reviewed" for r in eligible if r.id in uses):
        labels.append("unreviewed_food_data")
    if any(f.is_test_fixture for f in used_foods):
        labels.append("test_fixture_data")
    total = known_total() if req.weekly_budget is not None else None
    met: Optional[bool] = None
    if req.weekly_budget is not None:
        if unpriced:
            reasons.append("NUT-PRICE-MISSING")                        # budget cannot be verified: say so instead of guessing prices
        else:
            met = total <= req.weekly_budget
            if not met:
                reasons.append("NUT-BUDGET-EXCEEDED")
    if pn and any(not (pn[0] * 0.8 <= d.protein_g <= pn[1] * 1.2) for d in days):
        reasons.append("NUT-PROTEIN-OUTSIDE-RANGE-SOME-DAYS")
    return MealPlanResult("OK", tuple(reasons), tuple(days), tuple(shopping), None if total is None else round(total, 2), tuple(sorted(unpriced)), met,
                          tuple(labels), target, nutrition.safety_decision_id)

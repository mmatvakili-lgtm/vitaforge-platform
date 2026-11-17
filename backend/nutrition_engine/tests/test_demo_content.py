"""Demo nutrition content must be valid, honest (pending_review, sourced) and good enough that EVERY allergen/diet combination gets a plan."""
import datetime

import pytest

from nutrition_engine import NutritionProfile, estimate
from nutrition_engine.demo_content import demo_content
from nutrition_engine.food import ALLERGENS, DIET_TAGS, validate_food
from nutrition_engine.planner import MealPlanRequest, plan_week
from nutrition_engine.recipes import validate_recipe
from safety_core import SafetyCore
from safety_core.models import RuleSet, SafetyRequest

GATE = SafetyCore(RuleSet(version=1, status="t", screening_questions=("c",), allow_unreviewed_content=True, advisory_mode=True))
BASE = SafetyRequest("u", 30, True, {"c": False})
SCR = {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}


def test_every_food_and_recipe_is_valid_sourced_and_never_marked_reviewed():
    foods, recipes = demo_content()
    assert len(foods) >= 50 and len(recipes) >= 30
    for f in foods.values():
        assert not validate_food(f) and f.status == "pending_review" and f.source and f.source.dataset == "usda_fdc_foundation"
        assert f.source.license_verified is False and f.allergens_known and f.name_fa and "kcal" in f.per_100g
    for r in recipes:
        assert not validate_recipe(r, foods) and r.status == "pending_review" and r.steps and r.name_fa


@pytest.mark.parametrize("sex,weight", [("male", 80), ("female", 55)])
def test_every_allergen_and_diet_combination_gets_a_week_plan(sex, weight):
    foods, recipes = demo_content()
    n = estimate(NutritionProfile(age=30, sex=sex, height_cm=175, weight_kg=weight, activity="moderate", screening=SCR), GATE, BASE)
    combos = [((), ())] + [((a,), ()) for a in ALLERGENS] + [((), (d,)) for d in DIET_TAGS] + [(("milk", "egg"), ("vegan",)), (("tree_nut", "peanut"), ())]
    for al, dt in combos:
        r = plan_week(MealPlanRequest(today=datetime.date.today(), allergens=al, diet_required=dt, allow_unreviewed=True), n, foods, recipes)
        assert r.status == "OK", (sex, al, dt, r.reasons)
        used = {i.food_id for d in r.days for m in d.meals for i in m.ingredients}
        assert not any(set(foods[f].allergens) & set(al) for f in used)

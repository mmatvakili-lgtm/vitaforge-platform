import dataclasses
import random
import pytest
from app_services.errors import NotFound, ValidationFailed
from app_services.store import InMemoryStore
from nutrition_engine import FoodItem, NutritionConfig, NutritionLog, NutritionProfile, estimate, filter_foods
from nutrition_engine.engine import _bmr
from safety_core import SafetyCore
from safety_core.models import OutOfScopeFlag, RuleSet, SafetyRequest

Q = ("chest_pain",)
GATE = SafetyCore(RuleSet(version=1, status="t", screening_questions=Q, allow_unreviewed_content=True))
BASE = SafetyRequest("u", 30, True, {"chest_pain": False})
SCR = {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}


def prof(**kw):
    d = dict(age=30, sex="male", height_cm=180, weight_kg=80, activity="moderate", screening=SCR)
    d.update(kw)
    return NutritionProfile(**d)


def test_mifflin_reference_values():
    assert _bmr("male", 80, 180, 30) == 1780 and _bmr("female", 60, 165, 30) == 1320.25      # hand-computed from the published formula


def test_estimate_ok_ranges_and_labels():
    r = estimate(prof(), GATE, BASE)
    assert r.status == "OK" and r.bmr == (1602, 1780, 1958) and r.tdee == (2483, 2759, 3035)
    assert r.uncertainty == "medium" and "unverified_parameters" in r.labels and r.goal_adjustment == "disabled_pending_expert_review"
    assert r.macros["protein_g"] == (96, 160) and r.water_ml == (2400, 2800)
    assert estimate(prof(sex=None), GATE, BASE).uncertainty == "high"
    r2 = estimate(prof(sex=None), GATE, BASE)
    assert r2.bmr[0] < 1780 < r2.bmr[2]                    # range spans both sex equations


def test_goal_targets_disabled_until_reviewed():
    r = estimate(prof(goal="lose"), GATE, BASE)
    assert r.status == "OK" and "NUT-R03:goal-targets-disabled" in r.reasons and r.goal_adjustment == "disabled_pending_expert_review"
    assert estimate(prof(goal="lose"), GATE, BASE, NutritionConfig(bounds_reviewed=True)).goal_adjustment == "enabled"


def test_production_hides_unverified_ranges():
    r = estimate(prof(), GATE, BASE, NutritionConfig(show_unverified_ranges=False))
    assert r.macros is None and r.water_ml is None and r.tdee


@pytest.mark.parametrize("kw,reason", [(dict(screening={**SCR, "eating_disorder_risk": True}), "NUT-R02"),
                                       (dict(screening={**SCR, "medical_diet_needed": True}), "NUT-R04"),
                                       (dict(screening={**SCR, "pregnant_or_lactating": True}), "NUT-R04"),
                                       (dict(weight_kg=45, height_cm=190), "NUT-OUT-OF-RANGE-GUARD"),
                                       (dict(weight_kg=200, height_cm=170), "NUT-OUT-OF-RANGE-GUARD"),
                                       (dict(age=85), "NUT-OUT-OF-RANGE-GUARD")])
def test_refer_cases_give_no_numbers(kw, reason):
    r = estimate(prof(**kw), GATE, BASE)
    assert r.status == "REFER" and reason in r.reasons and r.tdee is None and r.macros is None


def test_blocked_by_safety_and_needs_info():
    assert estimate(prof(), GATE, dataclasses.replace(BASE, age_years=16)).status == "BLOCKED"
    assert estimate(prof(), GATE, dataclasses.replace(BASE, out_of_scope_flags=(OutOfScopeFlag("pregnancy"),))).status == "BLOCKED"
    r = estimate(prof(age=None, screening={}), GATE, BASE)
    assert r.status == "NEEDS_INFO" and "age" in r.questions and "screening:eating_disorder_risk" in r.questions
    assert estimate(prof(activity="x"), GATE, BASE).status == "NEEDS_INFO"
    assert estimate(prof(weight_kg=5), GATE, BASE).status == "NEEDS_INFO"


def test_food_filter_property_no_allergen_ever_passes():
    rnd = random.Random(3)
    al = ["milk", "egg", "peanut", "gluten", "soy"]
    for _ in range(300):
        foods = [FoodItem(str(i), "f", tuple(rnd.sample(al, rnd.randint(0, 2))), tuple(rnd.sample(al, rnd.randint(0, 1))),
                          tuple(rnd.sample(["vegetarian", "halal"], rnd.randint(0, 2))), rnd.choice([None, "src"]), rnd.choice([None, "2026-01-01"]))
                 for i in range(12)]
        user = tuple(rnd.sample(al, rnd.randint(1, 3)))
        for f in filter_foods(foods, user):
            assert not set(user) & (set(f.allergens) | set(f.traces)) and f.source and f.source_date


def test_food_filter_diet_and_case():
    a = FoodItem("a", "x", ("Milk",), (), ("halal",), "s", "d"); b = FoodItem("b", "y", (), (), ("halal", "vegetarian"), "s", "d")
    assert filter_foods([a, b], ["milk"]) == (b,) and filter_foods([a, b], diet_required=["vegetarian"]) == (b,)


def test_logbook():
    s = InMemoryStore(); n = NutritionLog(s, lambda: 10)
    e = n.add_meal("u", "Oats", kcal=350, protein_g=12); n.add_meal("u", "Snack", kcal=150); n.add_water("u", 500)
    sm = n.day_summary("u")
    assert sm["kcal"] == 500 and sm["protein_g"] == 12 and sm["water_ml"] == 500 and sm["completeness"]["protein_g"] == "1/2"
    assert "vs_estimate" in n.day_summary("u", estimate=estimate(prof(), GATE, BASE))
    assert n.history("u", 0, 20) == [{"day": 10, "meals": 2}]
    n.delete_meal("u", e.id)
    with pytest.raises(NotFound):
        n.delete_meal("u", e.id)
    for bad in (dict(name=""), dict(name="x"), dict(name="x", kcal=-1), dict(name="x", kcal=True), dict(name="x", kcal=99999)):
        with pytest.raises(ValidationFailed):
            n.add_meal("u", **bad)
    with pytest.raises(ValidationFailed):
        n.add_water("u", 5)

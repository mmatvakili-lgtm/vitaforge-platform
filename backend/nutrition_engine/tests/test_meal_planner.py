"""Planner behaviour on SYNTHETIC fixtures (round numbers, 'fixture' names). They are not food data and never ship as content."""
from datetime import date, timedelta

import pytest

from nutrition_engine import NutritionResult, PriceBook, PriceQuote, Recipe, FoodRecord, MealPlanRequest, plan_week
from nutrition_engine.fdc_import import import_fdc
from nutrition_engine.food import validate_food
from nutrition_engine.planner import assert_no_fixtures

TODAY = date(2026, 11, 10)
OK = NutritionResult("OK", ("NUT-ESTIMATE",), tdee=(2000, 2200, 2400), macros={"protein_g": (80, 140), "fat_g": (50, 90), "carbs_g": (200, 300)}, safety_decision_id="d1")


def food(i, kcal, p, f, c, **kw):
    kw.setdefault("allergens_known", True)
    return FoodRecord(id=i, name_en=f"Fixture food {i}", per_100g={"kcal": kcal, "protein_g": p, "fat_g": f, "carbs_g": c}, is_test_fixture=True, **kw)


FOODS = {f.id: f for f in (
    food("a", 350, 12, 3, 70, diet_tags=("vegetarian", "vegan")), food("b", 120, 20, 3, 0),
    food("c", 60, 2, 0, 12, diet_tags=("vegetarian", "vegan")), food("d", 400, 10, 30, 20, allergens=("tree_nut",), diet_tags=("vegetarian", "vegan")),
    food("e", 150, 8, 8, 10, allergens=("milk",), diet_tags=("vegetarian",)), food("u", 100, 5, 1, 15, allergens_known=False))}


def rec(i, ings, slots=("breakfast", "lunch", "dinner", "snack"), mins=20, servings=1):
    return Recipe(id=i, name_en=f"Fixture recipe {i}", slots=slots, ingredients=tuple(ings), servings=servings, cook_minutes=mins, is_test_fixture=True)


RECIPES = [rec("r1", [("a", 120), ("c", 150)]), rec("r2", [("b", 200), ("a", 100)]), rec("r3", [("a", 100), ("e", 150), ("c", 100)]),
           rec("r4", [("b", 250), ("c", 200), ("a", 90)], mins=45), rec("r5", [("a", 90), ("d", 30), ("c", 100)]), rec("r6", [("u", 300), ("a", 50)])]


def run(**kw):
    allow = kw.pop("allow_unreviewed", True)
    prices = kw.pop("prices", PriceBook())
    recipes = kw.pop("recipes", RECIPES)
    return plan_week(MealPlanRequest(today=TODAY, allow_unreviewed=allow, **kw), OK, FOODS, recipes, prices)


def test_fixtures_are_valid_and_guarded():
    assert not [validate_food(f) for f in FOODS.values() if validate_food(f)]
    with pytest.raises(RuntimeError):
        assert_no_fixtures(FOODS, RECIPES)


@pytest.mark.parametrize("status", ["BLOCKED", "REFER", "NEEDS_INFO"])
def test_planner_refuses_unless_nutrition_gate_is_ok(status):
    n = NutritionResult(status, ("X",))
    r = plan_week(MealPlanRequest(today=TODAY, allow_unreviewed=True), n, FOODS, RECIPES)
    assert r.status == status and r.days == ()


def test_unreviewed_data_is_not_used_by_default():
    r = run(allow_unreviewed=False)
    assert r.status == "NEEDS_CONTENT" and r.days == ()


def test_weekly_plan_hits_energy_and_is_labelled():
    r = run()
    assert r.status == "OK" and len(r.days) == 7
    assert {"unreviewed_food_data", "test_fixture_data", "estimate", "not_medical_advice"} <= set(r.labels)
    assert "NUT-R03:goal-targets-disabled" in r.reasons
    for d in r.days:
        assert 0.6 * 2200 <= d.kcal <= 1.4 * 2200, d
    uses = {}
    for d in r.days:
        for m in d.meals:
            uses[m.recipe_id] = uses.get(m.recipe_id, 0) + 1
    assert max(uses.values()) <= 28                  # variety is encouraged, never required beyond caps


def test_unknown_or_present_allergens_are_excluded():
    r = run(allergens=("tree_nut",))
    ids = {m.recipe_id for d in r.days for m in d.meals}
    assert "r5" not in ids and "r6" not in ids        # tree nut present / allergen status unknown
    r2 = run(allergens=("milk", "tree_nut"))
    assert "r3" not in {m.recipe_id for d in r2.days for m in d.meals}
    r3 = run(allergens=("milk",), recipes=[RECIPES[5]])
    assert r3.status == "NEEDS_CONTENT"


def test_diet_requirement_needs_every_ingredient_tagged():
    r = run(diet_required=("vegan",))
    ids = {m.recipe_id for d in r.days for m in d.meals}
    assert r.status == "OK" and ids <= {"r1", "r5"}   # r2/r4 contain food b (untagged), r3 contains milk food e (vegetarian only), r6 unknown tags


def test_cooking_time_limit():
    r = run(max_cook_minutes=30)
    assert "r4" not in {m.recipe_id for d in r.days for m in d.meals}


def test_shopping_list_matches_meals():
    r = run(days=3)
    total = {}
    by_id = {x.id: x for x in RECIPES}
    for d in r.days:
        for m in d.meals:
            for fid, g in by_id[m.recipe_id].ingredients:
                total[fid] = total.get(fid, 0) + g * m.portion / by_id[m.recipe_id].servings
    for s in r.shopping:
        assert abs(s.grams - round(total[s.food_id])) <= 1


def prices(price, observed=TODAY, ids="abcdeu"):
    return PriceBook(PriceQuote(i, "IR-ISF", "IRR", price, observed, "fixture-survey", "survey") for i in ids)


def test_budget_needs_currency_and_region():
    assert run(weekly_budget=1.0).status == "NEEDS_INFO"


def test_missing_or_stale_prices_make_budget_unverifiable_not_guessed():
    r = run(weekly_budget=1_000_000, currency="IRR", region="IR-ISF")
    assert "NUT-PRICE-MISSING" in r.reasons and r.budget_met is None and r.unpriced_food_ids
    stale = run(weekly_budget=1_000_000, currency="IRR", region="IR-ISF", prices=prices(1000, TODAY - timedelta(days=200)))
    assert stale.budget_met is None and "NUT-PRICE-MISSING" in stale.reasons


def test_budget_met_and_exceeded_with_fresh_prices():
    cheap = run(weekly_budget=10**9, currency="IRR", region="IR-ISF", prices=prices(1000))
    assert cheap.budget_met is True and cheap.total_cost is not None
    tight = run(weekly_budget=1, currency="IRR", region="IR-ISF", prices=prices(1000))
    assert tight.budget_met is False and "NUT-BUDGET-EXCEEDED" in tight.reasons and tight.status == "OK"


def test_budget_repair_lowers_cost():
    pb = PriceBook([PriceQuote(i, "IR-ISF", "IRR", p, TODAY, "fixture-survey") for i, p in (("a", 1000), ("b", 90000), ("c", 1000), ("d", 5000), ("e", 4000), ("u", 1000))])
    loose = run(weekly_budget=10**9, currency="IRR", region="IR-ISF", prices=pb)
    squeezed = run(weekly_budget=loose.total_cost * 0.8, currency="IRR", region="IR-ISF", prices=pb)
    assert squeezed.total_cost <= loose.total_cost


def test_pantry_items_cost_nothing_and_flagged():
    r = run(weekly_budget=10**9, currency="IRR", region="IR-ISF", prices=prices(1000), pantry=("a",))
    assert all(s.cost is None for s in r.shopping if s.in_pantry)


def test_price_book_rejects_invalid_quotes():
    with pytest.raises(ValueError):
        PriceBook([PriceQuote("a", "IR", "IRR", 0, TODAY, "x")])
    with pytest.raises(ValueError):
        PriceBook([PriceQuote("a", "IR", "IRR", 5, TODAY, "")])


FDC = {"FoundationFoods": [{"fdcId": 1, "description": "Fixture item", "publicationDate": "4/1/2019", "foodCategory": {"description": "Fixture"},
        "foodNutrients": [{"nutrient": {"number": "203", "name": "Protein", "unitName": "G"}, "amount": 10},
                          {"nutrient": {"number": "208", "name": "Energy", "unitName": "KCAL"}, "amount": 100},
                          {"nutrient": {"number": "204", "name": "Total lipid (fat)", "unitName": "G"}, "amount": 2},
                          {"nutrient": {"number": "205", "name": "Carbohydrate, by difference", "unitName": "G"}, "amount": 15},
                          {"nutrient": {"number": "307", "name": "Sodium, Na", "unitName": "G"}, "amount": 1}],   # wrong unit -> must be dropped
        "foodPortions": [{"gramWeight": 50, "portionDescription": "1 piece"}, {"gramWeight": 0, "portionDescription": "bad"}]}]}


def test_fdc_importer_is_conservative():
    rep = import_fdc(FDC, "2026-11-10")
    assert len(rep.accepted) == 1 and rep.nutrient_mismatches == 1
    f = rep.accepted[0]
    assert f.per_100g == {"kcal": 100.0, "protein_g": 10.0, "fat_g": 2.0, "carbs_g": 15.0}
    assert f.status == "pending_review" and f.allergens_known is False and f.source.license_verified is False
    assert f.serving_g == {"1 piece": 50.0}
    with pytest.raises(ValueError):
        import_fdc({"nope": []}, "x")


def test_endpoint_without_reviewed_data_is_needs_content_not_invented():
    from contract.harness import Harness
    h = Harness()
    t = h.login("nut@ex.com")
    h.onboard(t)
    h.call("PUT", "/nutrition/profile", {"sex": "male", "height_cm": 175, "weight_kg": 70, "activity": "moderate", "goal": "maintain",
                                           "screening": {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}}, token=t, check=False)
    r = h.call("POST", "/nutrition/meal-plan", {"days": 7}, token=t, check=False)
    assert r.status == 200 and r.body["status"] == "NEEDS_CONTENT" and r.body["days"] == []


def test_fdc_preserves_identifiers_units_basis_and_flags_duplicates():
    import copy
    d = copy.deepcopy(FDC)
    d["FoundationFoods"].append(copy.deepcopy(d["FoundationFoods"][0]))                       # same id twice
    other = copy.deepcopy(d["FoundationFoods"][0]); other["fdcId"] = 2                       # same description, different id
    d["FoundationFoods"].append(other)
    rep = import_fdc(d, "2026-11-10")
    assert [x["kind"] for x in rep.duplicates] == ["same_id", "same_description"]
    f = rep.accepted[0]
    assert f.basis == "per_100g" and f.source.record_id == "1" and f.id == "fdc_1"
    assert f.nutrient_refs["protein_g"] == {"id": "203", "unit": "G", "name": "Protein"}
    assert f.nutrient_refs["kcal"]["unit"] == "KCAL"
    assert set(f.nutrient_refs) == set(f.per_100g)
    assert rep.accepted[1].id == "fdc_2"                                                      # duplicates by description are kept but flagged, never merged silently


def test_fdc_rejects_physically_impossible_values_and_flags_energy_mismatch():
    import copy
    d = copy.deepcopy(FDC)
    d["FoundationFoods"][0]["foodNutrients"][0]["amount"] = 140                               # 140 g protein per 100 g
    assert import_fdc(d, "x").rejected
    d2 = copy.deepcopy(FDC)
    d2["FoundationFoods"][0]["foodNutrients"][1]["amount"] = 900                              # kcal far from macros
    rep = import_fdc(d2, "x")
    assert rep.energy_warnings == ["fdc_1"]


def test_prices_are_not_part_of_food_records():
    assert not any("price" in k for k in FoodRecord.__dataclass_fields__)

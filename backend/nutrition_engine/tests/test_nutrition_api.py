"""Contract-level behaviour of API-NUT-001..003: auth, consent, strict input, safety gating, no invented plans."""
from datetime import date

from contract.harness import Harness
from nutrition_engine import FoodRecord, PriceQuote, Recipe

SC = {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}
PROFILE = {"sex": "male", "height_cm": 175, "weight_kg": 70, "activity": "moderate", "goal": "maintain", "screening": SC}


def ready(email="n1@ex.com", consent=True):
    h = Harness()
    t = h.login(email)
    h.onboard(t, consent=consent)
    return h, t


def put(h, t, body):
    return h.call("PUT", "/nutrition/profile", body, token=t, check=False)


def test_requires_authentication():
    h = Harness()
    for m, p, b in (("PUT", "/nutrition/profile", PROFILE), ("GET", "/nutrition/estimate", None), ("POST", "/nutrition/meal-plan", {})):
        assert h.call(m, p, b, check=False).status == 401


def test_requires_health_data_consent():
    h, t = ready("n2@ex.com", consent=False)
    for m, p, b in (("PUT", "/nutrition/profile", PROFILE), ("GET", "/nutrition/estimate", None), ("POST", "/nutrition/meal-plan", {})):
        r = h.call(m, p, b, token=t, check=False)
        assert r.status == 403 and r.body["code"] == "consent_required", (p, r.status)


def test_strict_input_validation():
    h, t = ready("n3@ex.com")
    bad = [{**PROFILE, "role": "admin"}, {**PROFILE, "height_cm": 20}, {**PROFILE, "weight_kg": "70"}, {**PROFILE, "activity": "x"},
           {**PROFILE, "goal": "bulk_fast"}, {**PROFILE, "screening": {"eating_disorder_risk": False}}, {**PROFILE, "screening": {**SC, "medical_diet_needed": None}},
           {k: v for k, v in PROFILE.items() if k != "screening"}]
    for b in bad:
        assert put(h, t, b).status in (400, 422), b
    assert h.call("POST", "/nutrition/meal-plan", {"days": 7, "is_admin": True}, token=t, check=False).status in (400, 422)


def test_estimate_before_profile_is_404_and_after_is_ok():
    h, t = ready("n4@ex.com")
    assert h.call("GET", "/nutrition/estimate", token=t, check=False).status == 404
    assert h.call("POST", "/nutrition/meal-plan", {}, token=t, check=False).status == 404
    r = put(h, t, PROFILE)
    assert r.status == 200 and r.body["status"] == "OK" and "not_medical_advice" in r.body["labels"]
    assert h.call("GET", "/nutrition/estimate", token=t).body["tdee"] == r.body["tdee"]


def test_safety_screens_refer_and_block_meal_planning():
    for key in ("eating_disorder_risk", "medical_diet_needed", "pregnant_or_lactating"):
        h, t = ready(f"n5{key[:3]}@ex.com")
        r = put(h, t, {**PROFILE, "screening": {**SC, key: True}})
        assert r.status == 200 and r.body["status"] == "REFER" and r.body["tdee"] is None
        p = h.call("POST", "/nutrition/meal-plan", {}, token=t).body
        assert p["status"] == "REFER" and p["days"] == []                         # no meal plan for referred users


def test_goal_lose_gives_no_deficit_target():
    h, t = ready("n6@ex.com")
    r = put(h, t, {**PROFILE, "goal": "lose"})
    assert r.body["goal_adjustment"] == "disabled_pending_expert_review"


def test_no_food_content_means_needs_content_never_a_plan():
    h, t = ready("n7@ex.com")
    put(h, t, PROFILE)
    p = h.call("POST", "/nutrition/meal-plan", {"days": 7}, token=t).body
    assert p["status"] == "NEEDS_CONTENT" and p["days"] == [] and p["shopping"] == []


def _seed(h):
    foods = {"a": FoodRecord("a", "Fixture food a", per_100g={"kcal": 350, "protein_g": 12, "fat_g": 3, "carbs_g": 70}, allergens_known=True, is_test_fixture=True),
             "c": FoodRecord("c", "Fixture food c", per_100g={"kcal": 60, "protein_g": 2, "fat_g": 0, "carbs_g": 12}, allergens_known=True, is_test_fixture=True),
             "m": FoodRecord("m", "Fixture food m", per_100g={"kcal": 150, "protein_g": 8, "fat_g": 8, "carbs_g": 10}, allergens=("milk",), allergens_known=True, is_test_fixture=True)}
    h.store.__dict__.setdefault("foods", {}).update(foods)
    for i, ings in (("r1", [("a", 120), ("c", 150)]), ("r2", [("a", 100), ("m", 150), ("c", 100)])):
        h.store.__dict__.setdefault("recipes", {})[i] = Recipe(id=i, name_en=f"Fixture recipe {i}", slots=("breakfast", "lunch", "dinner", "snack"), ingredients=tuple(ings), steps=("Mix.",), is_test_fixture=True)
    for fid in foods:
        h.store.__dict__.setdefault("price_quotes", {})[f"{fid}|IR-ISF|IRR"] = PriceQuote(fid, "IR-ISF", "IRR", 1000.0, date.today(), "fixture-survey", "survey")


def test_plan_with_data_conforms_to_contract_and_is_labelled():
    h, t = ready("n8@ex.com")
    put(h, t, PROFILE)
    _seed(h)
    r = h.call("POST", "/nutrition/meal-plan", {"days": 3, "allergens": ["milk"], "weekly_budget": 1e9, "currency": "IRR", "region": "IR-ISF"}, token=t)
    assert r.status == 200 and r.body["status"] == "OK" and len(r.body["days"]) == 3
    assert {"unreviewed_food_data", "test_fixture_data"} <= set(r.body["labels"])
    assert all(m["name_en"] != "Fixture recipe r2" for d in r.body["days"] for m in d["meals"])      # milk excluded
    assert r.body["budget_met"] is True and r.body["shopping"]
    assert h.problems == []                                                                              # every response validated against the OpenAPI schema

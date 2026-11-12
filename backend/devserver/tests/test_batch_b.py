"""Safety-critical behaviour of the nutrition log: allergen alerts, REFER blocking, erase, user prices. Fixture foods are labelled test fixtures."""
import pytest

from contract.harness import PASSWORD, Harness
from nutrition_engine import FoodRecord, Recipe

SC = {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}


def food(i, allergens=(), known=True, kcal=100):
    return FoodRecord(i, f"Fixture {i}", per_100g={"kcal": kcal, "protein_g": 5, "fat_g": 1, "carbs_g": 20}, allergens=tuple(allergens), allergens_known=known, is_test_fixture=True)


@pytest.fixture()
def env():
    h = Harness()
    t = h.login("b@ex.com"); h.onboard(t)
    h.store.__dict__.setdefault("foods", {}).update({"milky": food("milky", ("milk",)), "plain": food("plain"), "mystery": food("mystery", known=False)})
    h.store.__dict__.setdefault("recipes", {})["rmilk"] = Recipe(id="rmilk", name_en="Fixture recipe", slots=("lunch",), ingredients=(("milky", 100), ("plain", 100)), steps=("Mix.",), is_test_fixture=True)
    return h, t


def profile(h, t, **kw):
    return h.call("PUT", "/nutrition/profile", {"sex": "male", "height_cm": 175, "weight_kg": 70, "activity": "moderate", "goal": "maintain", "screening": SC, **kw}, token=t)


def log(h, t, **body):
    return h.call("POST", "/nutrition/meals", {"slot": "lunch", **body}, token=t)


def test_allergen_alert_for_food_recipe_unknown_and_safe(env):
    h, t = env
    assert profile(h, t, allergens=["milk"]).status == 200
    a = log(h, t, food_id="milky", grams=100).body["allergen_alert"]
    assert a["allergens"] == ["milk"]
    u = log(h, t, food_id="mystery", grams=100).body["allergen_alert"]
    assert u["unknown"] is True and u["allergens"] == []            # missing data is never treated as safe
    assert log(h, t, food_id="plain", grams=100).body["allergen_alert"] is None
    r = log(h, t, recipe_id="rmilk", servings=1).body
    assert r["allergen_alert"] and "milk" in r["allergen_alert"]["allergens"]
    assert log(h, t, name="Manual", kcal=200).body["allergen_alert"] is None   # user-entered: no allergen data to judge


def test_no_alert_without_saved_allergens(env):
    h, t = env
    profile(h, t)
    assert log(h, t, food_id="milky", grams=100).body["allergen_alert"] is None


def test_refer_profile_cannot_log_and_sources_are_exclusive(env):
    h, t = env
    profile(h, t)
    assert log(h, t, food_id="plain", grams=100, recipe_id="rmilk", servings=1).status == 422
    assert log(h, t, grams=100).status == 422
    profile(h, t, screening={**SC, "medical_diet_needed": True})
    assert log(h, t, food_id="plain", grams=100).status == 409


def test_future_dates_rejected_and_delete_unknown_is_404(env):
    h, t = env
    profile(h, t)
    assert h.call("GET", "/nutrition/meals?date=2999-01-01", token=t).status in (400, 422)
    assert h.call("DELETE", "/nutrition/meals/00000000-0000-4000-8000-000000000009", token=t).status == 404


def test_erase_removes_nutrition_data(env):
    h, t = env
    profile(h, t)
    log(h, t, food_id="plain", grams=100)
    h.call("POST", "/nutrition/water", {"ml": 250}, token=t)
    h.call("PUT", "/nutrition/prices", {"food_id": "plain", "price_per_kg": 5, "currency": "USD", "region": "US"}, token=t)
    h.call("PUT", "/nutrition/shopping-state", {"checked": ["plain"]}, token=t)
    uid = next(iter(h.store.__dict__["meals"]))
    r = h.call("POST", "/privacy/delete", {"password": PASSWORD, "confirm": True}, token=t)
    assert r.status in (200, 202), r.body
    for k in ("meals", "water", "user_prices", "shopping_state", "nutrition_profiles"):
        assert uid not in h.store.__dict__.get(k, {}), k


def test_export_download_is_owner_only_includes_nutrition_expires_and_is_erased(env):
    h, t = env
    profile(h, t)
    log(h, t, food_id="plain", grams=100)
    rid = h.call("POST", "/privacy/export", token=t).body["id"]
    d = h.call("GET", f"/privacy/export/{rid}", token=t)
    assert d.status == 200 and d.body["nutrition"]["meals"] and "pw" not in str(d.body)
    t2 = h.login("other@ex.com"); h.onboard(t2)
    assert h.call("GET", f"/privacy/export/{rid}", token=t2).status == 404          # never another user's export
    assert h.call("GET", f"/privacy/export/{rid}", token=t).status == 200
    for r in h.store.privacy_requests.values():
        r["expires_at"] = 0
    assert h.call("GET", f"/privacy/export/{rid}", token=t).status == 410
    assert all("data" not in r for r in h.store.privacy_requests.values())


def test_erase_drops_stored_export_copies(env):
    h, t = env
    profile(h, t)
    h.call("POST", "/privacy/export", token=t)
    assert any("data" in r for r in h.store.privacy_requests.values())
    assert h.call("POST", "/privacy/delete", {"password": PASSWORD, "confirm": True}, token=t).status in (200, 202)
    assert not any("data" in r for r in h.store.privacy_requests.values() if r["kind"] == "export")


def test_food_review_queue_blocks_unsafe_approval_and_records_the_reviewer(env):
    from nutrition_engine.food import FoodSource
    h, t = env
    rev = h.login("nrev@ex.com", role="nutrition_reviewer")
    store_foods = h.store.__dict__["foods"]
    good = FoodRecord("real1", "Real food", per_100g={"kcal": 100, "protein_g": 5, "fat_g": 1, "carbs_g": 20}, allergens_known=True,
                      nutrient_refs={k: {"id": "x", "unit": "g", "name": k} for k in ("kcal", "protein_g", "fat_g", "carbs_g")},
                      source=FoodSource("usda_fdc_foundation", "1", license="CC0-1.0", license_verified=True))
    nolic = FoodRecord("real2", "No license", per_100g={"kcal": 100}, allergens_known=True, nutrient_refs={"kcal": {"id": "x", "unit": "kcal", "name": "k"}}, source=FoodSource("usda_fdc_foundation", "2"))
    store_foods.update({"real1": good, "real2": nolic})
    assert h.call("GET", "/admin/foods", token=t).status == 403                    # normal users never see the queue
    assert h.call("POST", "/admin/foods/real1/review", {"decision": "approve"}, token=t).status == 403
    q = {f["id"]: f for f in h.call("GET", "/admin/foods", token=rev).body}
    assert q["milky"]["approval_blockers"] == ["test_fixture", "no_source"] and q["real2"]["approval_blockers"] == ["license_not_verified"]
    r = h.call("POST", "/admin/foods/real2/review", {"decision": "approve"}, token=rev)
    assert r.status == 409 and store_foods["real2"].status == "pending_review"       # blocked: nothing changes
    assert h.call("POST", "/admin/foods/real1/review", {"decision": "reject"}, token=rev).status == 422   # a reason is mandatory
    ok = h.call("POST", "/admin/foods/real1/review", {"decision": "approve", "notes": "checked against FDC"}, token=rev)
    assert ok.status == 200 and ok.body["status"] == "reviewed" and ok.body["reviewed_by"] and ok.body["review_notes"] == "checked against FDC"
    assert h.call("POST", "/admin/foods/real1/review", {"decision": "retire", "notes": "superseded"}, token=rev).body["status"] == "retired"
    assert h.call("POST", "/admin/foods/real1/review", {"decision": "approve"}, token=rev).status == 409   # a retired food cannot be approved again
    assert h.call("POST", "/admin/foods/nope/review", {"decision": "approve"}, token=rev).status == 404

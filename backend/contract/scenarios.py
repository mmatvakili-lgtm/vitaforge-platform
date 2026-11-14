"""Deterministic scenarios that exercise every OpenAPI operation (success paths) and each reachable declared error."""
from __future__ import annotations

import re
import uuid
from typing import Dict

from contract.harness import DOB, PASSWORD, Harness
from devserver.app import SCREENING

RANDOM_ID = "11111111-2222-4333-8444-555555555555"


def happy_path(h: Harness) -> Dict[str, str]:
    c = h.call
    c("GET", "/health/live"); c("GET", "/health/ready")
    t = h.login("user@ex.com")
    adm = h.login("adm@ex.com", role="admin")
    rev = h.login("rev@ex.com", role="clinical_safety_reviewer")
    cad = h.login("cad@ex.com", role="content_admin")
    # profile / privacy / onboarding / body
    c("GET", "/profile", token=t); c("PATCH", "/profile", {"display_name": "Ali", "country": "IR", "language": "fa", "unit_system": "metric"}, token=t)
    h.onboard(t)
    c("GET", "/onboarding", token=t); c("POST", "/onboarding/complete", token=t)
    for m, v, u in (("height", 175, "cm"), ("weight", 70, "kg"), ("waist", 80, "cm")):
        c("POST", "/body/measurements", {"metric": m, "value": v, "unit": u, "source": "measured"}, token=t)
    c("GET", "/assessment", token=t)
    c("PUT", "/assessment", token=t, body={"answers": {"squat_reps": 20, "push_variant": "knee", "push_reps": 8, "plank_s": 40}})
    c("GET", "/body/overview", token=t)
    # catalog + plan
    ex = c("GET", "/exercises?page=1&page_size=5", token=t).body
    eid = ex["results"][0]["id"]
    c("GET", f"/exercises/{eid}", token=t); c("GET", f"/exercises/{eid}/alternatives", token=t)
    gen = c("POST", "/workouts/generate", {"preferred_structure": "auto"}, token=t)
    plan = gen.body["plan"]
    c("GET", "/workouts/current", token=t); c("GET", f"/workouts/plans/{plan['plan_id']}/versions", token=t)
    wex = plan["days"][0]["exercises"][0]["workout_exercise_id"]
    c("POST", f"/workouts/plans/{plan['plan_id']}/substitute", {"workout_exercise_id": wex, "reason": "preference"}, token=t)
    plan = c("GET", "/workouts/current", token=t).body
    # session logging
    day = plan["days"][0]
    ss = c("POST", "/workouts/sessions", {"day_id": day["day_id"]}, token=t).body
    e0 = day["exercises"][0]["exercise_id"]
    for n, load in ((1, 20), (2, 25)):
        c("POST", f"/workouts/sessions/{ss['id']}/logs", {"client_uuid": str(uuid.uuid4()), "exercise_id": e0, "set_no": n, "reps": 8, "load_kg": load, "rpe": 7}, token=t)
    c("POST", f"/workouts/sessions/{ss['id']}/finish", {"perceived_difficulty": 6}, token=t)
    c("GET", "/workouts/progression", token=t)
    c("GET", "/workouts/sessions", token=t); c("GET", "/progress/weekly", token=t); c("GET", "/progress/monthly", token=t); c("GET", "/dashboard", token=t)
    # health (after the plan so the plan flow is unaffected)
    cond = c("POST", "/health/conditions", {"region": "lower_back", "problem_type": "pain", "self_severity": 0, "side": "na", "trend": "better"}, token=t).body
    c("PATCH", f"/health/conditions/{cond['id']}", {"self_severity": 2, "trend": "same"}, token=t)
    c("POST", "/health/symptoms", {"context": "checkin", "region": "knee", "severity": 1, "note": "x"}, token=t)
    c("POST", "/health/pain-logs", {"region": "knee", "intensity": 3, "timing": "after"}, token=t)
    c("GET", "/health/profile", token=t)
    t2 = h.login("oos@ex.com"); h.onboard(t2)
    c("POST", "/health/out-of-scope-flags", {"flag_type": "pregnancy"}, token=t2)
    # subscriptions / AI
    c("GET", "/subscriptions/plans"); c("GET", "/subscriptions/me", token=t)
    c("POST", "/subscriptions/checkout", {"plan_code": "pro", "billing_cycle": "monthly"}, token=t)
    h.store.subs[h.store.by_email["user@ex.com"]] = {"plan": "pro", "active": True}                  # as a verified payment webhook would
    c("POST", "/ai/chat", {"purpose": "general", "message": "چرا این برنامه؟"}, token=t)
    c("POST", "/subscriptions/cancel", token=t)
    # nutrition (profile -> estimate -> meal plan; no food content exists, so the plan must be NEEDS_CONTENT)
    c("PUT", "/nutrition/profile", {"sex": "male", "height_cm": 175, "weight_kg": 70, "activity": "moderate", "goal": "maintain",
                                    "screening": {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}}, token=t)
    c("GET", "/nutrition/estimate", token=t)
    c("POST", "/nutrition/meal-plan", {"days": 7}, token=t)
    # nutrition catalog / logging / prices / shopping (labelled test fixtures only, isolated to this harness store)
    from nutrition_engine import FoodRecord, Recipe
    tn = h.login("nut@ex.com"); h.onboard(tn)       # a user without conditions, so the Safety Core lets nutrition through
    c("PUT", "/nutrition/profile", {"sex": "male", "height_cm": 175, "weight_kg": 70, "activity": "moderate", "goal": "maintain",
                                    "screening": {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}}, token=tn)
    h.store.__dict__.setdefault("foods", {}).update({
        "fx_a": FoodRecord("fx_a", "Fixture food a", per_100g={"kcal": 350, "protein_g": 12, "fat_g": 3, "carbs_g": 70}, allergens_known=True, is_test_fixture=True),
        "fx_c": FoodRecord("fx_c", "Fixture food c", per_100g={"kcal": 60, "protein_g": 2, "fat_g": 0, "carbs_g": 12}, allergens_known=True, is_test_fixture=True)})
    h.store.__dict__.setdefault("recipes", {})["fx_r1"] = Recipe(id="fx_r1", name_en="Fixture recipe r1", slots=("breakfast", "lunch", "dinner", "snack"),
                                                                 ingredients=(("fx_a", 120), ("fx_c", 150)), steps=("Mix.",), is_test_fixture=True)
    c("GET", "/foods", token=tn); c("GET", "/foods/fx_a", token=tn); c("GET", "/recipes", token=tn); c("GET", "/recipes/fx_r1", token=tn)
    ml = c("POST", "/nutrition/meals", {"slot": "lunch", "food_id": "fx_a", "grams": 150}, token=tn).body
    c("POST", "/nutrition/meals", {"slot": "dinner", "recipe_id": "fx_r1", "servings": 1}, token=tn)
    c("GET", "/nutrition/meals", token=tn); c("GET", "/nutrition/summary", token=tn)
    c("DELETE", f"/nutrition/meals/{ml['id']}", token=tn)
    c("POST", "/nutrition/water", {"ml": 250}, token=tn)
    c("GET", "/nutrition/prices", token=tn)
    c("PUT", "/nutrition/prices", {"food_id": "fx_a", "price_per_kg": 100.0, "currency": "USD", "region": "US"}, token=tn)
    c("DELETE", "/nutrition/prices/fx_a", token=tn)
    nrev = h.login("nrev@ex.com", role="nutrition_reviewer")                     # review queue: a test fixture can never be approved
    c("GET", "/admin/foods", token=nrev)
    c("POST", "/admin/foods/fx_a/review", {"decision": "approve"}, token=nrev)       # -> 409 (test_fixture blocker)
    c("POST", "/admin/foods/fx_c/review", {"decision": "reject", "notes": "fixture only, not real data"}, token=nrev)
    c("PUT", "/nutrition/shopping-state", {"checked": ["fx_a"]}, token=tn); c("GET", "/nutrition/shopping-state", token=tn)
    # admin
    c("GET", "/admin/exercises", token=cad)
    cr = c("POST", "/admin/exercises", {"stable_code": "new_ex", "movement_pattern": "core", "difficulty": "beginner", "muscles": ["abs"]}, token=cad).body
    c("POST", f"/admin/exercises/{cr['id']}/transition", {"to_status": "scientific_review"}, token=cad)
    c("GET", "/admin/safety/rule-sets", token=rev)
    h.store.rule_sets[7] = {"status": "draft_unreviewed"}
    rs = next(x for x in c("GET", "/admin/safety/rule-sets", token=rev).body if x["version"] == 7)
    c("POST", f"/admin/safety/rule-sets/{rs['id']}/publish", {"confirm_sources_attached": True, "notes": "EXP-TEST-REF"}, token=rev)
    c("GET", "/admin/users", token=adm)
    pid = c("GET", "/subscriptions/plans").body["plans"][0]
    from devserver.app import pub
    c("PUT", f"/admin/plans/{pub('plan_code', 'free')}/features", {"features": [{"code": "ai_chat", "enabled": False}]}, token=adm)
    c("POST", "/admin/health-access-grants", {"grantee_id": RANDOM_ID, "subject_user_id": RANDOM_ID, "reason": "support request ticket", "duration_minutes": 30}, token=adm)
    # auth lifecycle
    t3 = h.login("life@ex.com")
    c("GET", "/auth/sessions", token=t3)
    t3b = h.login("life@ex.com")
    sess = c("GET", "/auth/sessions", token=t3).body
    other = next(s for s in sess if not s["current"])
    c("DELETE", f"/auth/sessions/{other['id']}", token=t3)
    c("POST", "/auth/logout", token=t3)
    c("POST", "/auth/password-reset/request", {"identifier": "life@ex.com"})
    c("POST", "/auth/password-reset/confirm", {"token": h.captured("life@ex.com", "password_reset")["secret"], "new_password": "An0therStrongPass"})
    # verify flow + privacy (own apps/users)
    v = Harness(dev=True)
    v.register("ver@ex.com")
    v.store.mail_limits.clear()                                   # the cooldown would (correctly) answer 429; clear it to exercise the success path
    v.call("POST", "/auth/verify/resend", {"identifier": "ver@ex.com"})
    v.call("POST", "/auth/verify", {"identifier": "ver@ex.com", "code": v.captured("ver@ex.com", "verification")["secret"]})
    # Telegram verification (primary channel)
    g = Harness(dev=True)
    g.register("tg@ex.com")
    g.verify_by_telegram("tg@ex.com", 700100)
    tg_tok = g.login("tg@ex.com")
    g.call("GET", "/telegram/status", token=tg_tok)
    g.call("PUT", "/telegram/notifications", {"enabled": True}, token=tg_tok)
    h.log.extend(v.log)
    h.log.extend(g.log)
    t4 = h.login("priv@ex.com")
    c("POST", "/privacy/export", token=t4)
    rid = c("POST", "/privacy/export", token=t4).body["id"]
    c("GET", f"/privacy/export/{rid}", token=t4)
    c("GET", f"/privacy/requests/{rid}", token=t4)
    c("POST", "/privacy/delete", {"password": PASSWORD, "confirm": True}, token=t4)
    return {"user": t, "admin": adm, "reviewer": rev, "content_admin": cad}

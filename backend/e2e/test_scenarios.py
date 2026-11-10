"""End-to-end scenarios over the HTTP adapter (OpenAPI contract shapes) with the starter catalog (experimental content, dev mode).

Every exchange is also validated against the OpenAPI document by the contract harness, so these scenarios cannot pass on a drifted API.
"""
from contract.harness import PASSWORD, Harness
from devserver.app import SCREENING, pub
from exercise_catalog import load_starter, relations, to_catalog_entry


def build(allow=True, caution_max_loading="low", dev=True):
    # caution_max_loading="low": EXP-002 placeholder, dev-only value, NOT expert approved (the safe default is "none")
    h = Harness(dev=dev, allow=allow, rule_kwargs={"caution_max_loading": caution_max_loading})
    rows = load_starter()
    h.store.catalog = {r.id: to_catalog_entry(r, dev_experimental=True) for r in rows}
    h.store.relations = relations(rows)
    h.app.records = {r.id: r for r in rows}
    h.app.layer.kb.records = rows
    return h


def signup(h, email, age=30, level="beginner", goal="general_fitness", days=3, minutes=75, equipment=(), red=None):
    t = h.login(email)
    for n, d in ((1, {"age": age}), (2, {"goal": goal, "level": level}), (3, {"days_per_week": days, "session_minutes": minutes}), (4, {"equipment": list(equipment)})):
        assert h.call("PUT", f"/onboarding/steps/{n}", {"answers": d}, token=t).status == 200
    h.grant_consent(t)
    assert h.call("POST", "/health/screening", {"screening_version": 1, "answers": {q: (red == q) for q in SCREENING}}, token=t).status == 200
    assert h.call("POST", "/onboarding/complete", token=t).status == 200
    return t


def codes(h, plan):
    by = {pub("ex", c): c for c in h.store.catalog}
    return [by[e["exercise_id"]] for d in plan["days"] for e in d["exercises"]]


def generate(h, t):
    r = h.call("POST", "/workouts/generate", {}, token=t)
    assert r.problems == [], r.problems
    return r


def test_s1_home_beginner_no_equipment_full_cycle():
    h = build(); t = signup(h, "s1@ex.com")
    r = generate(h, t)
    plan = r.body["plan"]
    assert r.status == 200 and plan["rationale"]["label"] == "experimental" and r.body["decision"]["status"] in ("ALLOW", "ALLOW_WITH_MODIFICATION")
    cs = codes(h, plan)
    assert cs and all(h.store.catalog[c].candidate.equipment in ((), ("bodyweight",)) for c in cs)      # no gear => bodyweight only
    day = plan["days"][0]
    ex = day["exercises"][0]
    code = codes(h, {"days": [day]})[0]
    for _ in range(3):                                                  # three sessions logged -> progression decision is explainable
        sid = h.call("POST", "/workouts/sessions", {"day_id": day["day_id"]}, token=t).body["id"]
        for n in range(1, 4):
            assert h.call("POST", f"/workouts/sessions/{sid}/logs", {"client_uuid": f"00000000-0000-4000-8000-{len(h.log):012d}", "exercise_id": ex["exercise_id"],
                                                                     "set_no": n, "reps": 12, "load_kg": 0, "rpe": 6.5}, token=t).status == 201
        assert h.call("POST", f"/workouts/sessions/{sid}/finish", {}, token=t).status == 200
    prog = h.call("GET", f"/workouts/progression/{code}", token=t).body
    assert prog["action"] in ("increase_reps", "increase_load", "hold", "suggest_deload") and prog["reasons"]
    assert h.call("GET", "/progress/weekly", token=t).body["completed_sessions"] == 3
    assert h.call("GET", "/dashboard", token=t).body["current_plan"]["label"] == "experimental"
    assert h.problems == []


def test_s2_gym_intermediate_gets_loaded_exercises():
    h = build(); t = signup(h, "s2@ex.com", level="intermediate", goal="muscle_gain", days=4, minutes=120, equipment=["dumbbell", "bench", "barbell", "machine", "box", "band"])
    r = generate(h, t)
    assert r.status == 200 and r.body["plan"]["structure"] == "upper_lower"
    assert any(h.store.catalog[c].candidate.equipment for c in codes(h, r.body["plan"]))
    assert h.call("GET", "/safety/explain", token=t).body["items"]


def test_s3_back_history_without_pain_avoids_high_back_load_and_prefers_supportive():
    h = build(); t = signup(h, "s3@ex.com", level="intermediate", equipment=["dumbbell", "barbell", "bench", "box"], minutes=120)
    # history of a diagnosed injury, no current pain -> caution pathway
    r = h.call("POST", "/health/conditions", {"region": "lower_back", "problem_type": "diagnosed_injury"}, token=t)
    assert r.status == 201 and r.problems == []
    r = generate(h, t)
    assert r.status == 200 and r.body["plan"]
    cs = codes(h, r.body["plan"])
    assert "barbell_back_squat" not in cs and "dumbbell_romanian_deadlift" not in cs                 # high lower-back loading excluded
    assert {"dead_bug", "bird_dog", "glute_bridge"} & set(cs)                                         # supportive (experimental tags) preferred
    ex = h.call("GET", "/safety/explain", token=t).body
    rej = {i["code"]: i for i in ex["items"] if i["state"] == "rejected"}
    assert "barbell_back_squat" in rej and rej["barbell_back_squat"]["why"][0]["reason"] == "SAF-R301"


def test_s3b_back_pain_with_unknown_severity_is_treated_as_active_pain_and_blocks_plan():
    """Conservative derivation (EXP-014): a self-reported pain condition without severity counts as active pain."""
    h = build(); t = signup(h, "s3b@ex.com")
    h.call("POST", "/health/conditions", {"region": "lower_back", "problem_type": "pain"}, token=t)
    r = generate(h, t)
    assert r.body["plan"] is None and r.body["decision"]["status"] == "STOP_AND_REFER"
    # the user states there is no current pain -> history pathway, plan allowed
    cond = h.call("GET", "/health/profile", token=t).body["conditions"][0]
    assert h.call("PATCH", f"/health/conditions/{cond['id']}", {"self_severity": 0}, token=t).status == 200
    assert generate(h, t).body["plan"] is not None


def test_s4_new_knee_pain_no_plan_with_guidance_then_explain():
    h = build(); t = signup(h, "s4@ex.com")
    assert generate(h, t).body["plan"] is not None
    r = h.call("POST", "/health/pain-logs", {"region": "knee", "intensity": 6, "timing": "during"}, token=t)
    assert r.status == 201 and r.problems == [] and r.body["decision"]["status"] == "STOP_AND_REFER"
    r = generate(h, t)
    assert r.status == 200 and r.body["plan"] is None
    assert r.body["decision"]["status"] == "STOP_AND_REFER" and "SAF-R011" in [x["code"] for x in r.body["decision"]["reasons"]]
    chat = h.call("POST", "/ai/chat", {"purpose": "general", "message": "next session please"}, token=t)
    assert chat.status == 200 and chat.problems == [] and chat.body["mode"] == "rule_based_fallback"          # AI cannot talk around Safety
    assert chat.body["decision"]["status"] == "STOP_AND_REFER"
    assert chat.body["answer"] and chat.body["uncertainty"] in ("none", "low", "medium", "high")


def test_s5_red_flag_blocks_training_ai_and_nutrition():
    h = build(); t = signup(h, "s5@ex.com", red="chest_pain")
    r = generate(h, t)
    assert r.body["plan"] is None and r.body["decision"]["status"] == "STOP_AND_REFER"
    assert h.call("POST", "/ai/chat", {"purpose": "general", "message": "why this plan"}, token=t).body["mode"] == "rule_based_fallback"
    n = h.call("PUT", "/nutrition/profile", {"sex": "male", "height_cm": 180, "weight_kg": 80, "activity": "moderate",
                                               "screening": {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}}, token=t).body
    assert n["status"] == "BLOCKED" and n["tdee"] is None


def test_s6_eating_disorder_signal_refers_nutrition_but_training_continues():
    h = build(); t = signup(h, "s6@ex.com")
    n = h.call("PUT", "/nutrition/profile", {"sex": "female", "height_cm": 165, "weight_kg": 60, "activity": "light",
                                               "screening": {"eating_disorder_risk": True, "medical_diet_needed": False, "pregnant_or_lactating": False}}, token=t).body
    assert n["status"] == "REFER" and n["macros"] is None
    assert generate(h, t).body["plan"] is not None


def test_s7_production_mode_never_serves_sample_content():
    h = build(allow=False, dev=False); t = signup(h, "s7@ex.com")
    r = generate(h, t)
    assert r.body["plan"] is None and r.body["decision"]["status"] == "ERROR_FAILSAFE" and "SAF-R013" in [x["code"] for x in r.body["decision"]["reasons"]]
    assert h.call("POST", "/ai/chat", {"purpose": "general", "message": "next session"}, token=t).body["mode"] == "rule_based_fallback"
    assert h.call("GET", "/exercises", token=t).status == 200


def test_s8_substitution_preserves_safety_and_versions():
    h = build(); t = signup(h, "s8@ex.com", days=1, equipment=["dumbbell", "bench", "box", "band"], minutes=90)
    plan = generate(h, t).body["plan"]
    by = {pub("ex", c): c for c in h.store.catalog}
    target = next(e for d in plan["days"] for e in d["exercises"] if by[e["exercise_id"]] == "bodyweight_squat")
    r = h.call("POST", f"/workouts/plans/{plan['plan_id']}/substitute", {"workout_exercise_id": target["workout_exercise_id"], "reason": "equipment"}, token=t)
    assert r.status == 200 and r.problems == [] and r.body["version_no"] == 2
    new_codes = codes(h, r.body)
    assert "bodyweight_squat" not in new_codes and ({"goblet_squat", "box_squat"} & set(new_codes))
    vers = h.call("GET", f"/workouts/plans/{plan['plan_id']}/versions", token=t).body
    assert [v["version_no"] for v in vers] == [1, 2]
    assert h.problems == []

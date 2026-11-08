"""End-to-end scenarios over the HTTP adapter with the starter catalog (experimental content, dev mode)."""
import io
import json
import pytest
from app_services.store import InMemoryStore
from devserver.app import SCREENING, App
from exercise_catalog import load_starter, relations, to_catalog_entry
from safety_core.models import RuleSet


def build(allow=True, caution_max_loading="low"):
    rows = load_starter()
    s = InMemoryStore()
    s.catalog = {r.id: to_catalog_entry(r, dev_experimental=True) for r in rows}
    s.relations = relations(rows)
    # caution_max_loading: EXP-002 placeholder, dev-only value, NOT expert approved
    rs = RuleSet(version=0, status="e2e", screening_questions=SCREENING, allow_unreviewed_content=allow,
                 caution_max_loading=caution_max_loading)
    a = App(s, rs, dev_mode=True)
    a.layer.kb.records = rows
    return a


def call(app, method, path, body=None, token=None):
    data = json.dumps(body or {}).encode(); out = {}
    env = {"REQUEST_METHOD": method, "PATH_INFO": "/api/v1" + path, "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)}
    if token: env["HTTP_AUTHORIZATION"] = "Bearer " + token
    res = b"".join(app(env, lambda st, h: out.update(status=int(st.split()[0]))))
    return out["status"], json.loads(res)


def signup(a, email, age=30, level="beginner", goal="general_fitness", days=3, minutes=75, equipment=(), red=None):
    call(a, "POST", "/auth/register", {"email": email, "password": "Str0ngPassw0rd"})
    t = call(a, "POST", "/auth/login", {"email": email, "password": "Str0ngPassw0rd"})[1]["token"]
    for step, d in (("basics", {"age": age}), ("goal", {"goal": goal, "level": level}), ("schedule", {"days_per_week": days, "session_minutes": minutes}),
                    ("equipment", {"equipment": list(equipment)})):
        assert call(a, "PUT", f"/onboarding/steps/{step}", d, t)[0] == 200
    call(a, "POST", "/consents", {"type": "health_data_processing"}, t)
    call(a, "POST", "/health/screening", {q: (red == q) for q in SCREENING}, t)
    assert call(a, "POST", "/onboarding/complete", {}, t)[0] == 200
    return t


def codes(plan):
    return [e["code"] for d in plan["result"]["days"] for e in d["exercises"]]


def test_s1_home_beginner_no_equipment_full_cycle():
    a = build(); t = signup(a, "s1@ex.com")
    st, plan = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 200 and plan["result"]["label"] == "experimental"
    cs = codes(plan)
    assert cs and all(a.store.catalog[c].candidate.equipment in ((), ("bodyweight",)) for c in cs)      # no gear => bodyweight only
    day = plan["result"]["days"][0]
    code = day["exercises"][0]["code"]
    for week in range(3):                                                  # three sessions logged -> progression decision is explainable
        sid = call(a, "POST", "/workouts/sessions", {"day_name": day["name"]}, t)[1]["id"]
        for _ in range(3):
            assert call(a, "POST", f"/workouts/sessions/{sid}/logs", {"code": code, "reps": 12, "load_kg": 0, "rpe": 6.5}, t)[0] == 200
        call(a, "POST", f"/workouts/sessions/{sid}/finish", {}, t)
    prog = call(a, "GET", f"/workouts/progression/{code}", None, t)[1]
    assert prog["action"] in ("increase_reps", "increase_load", "hold", "suggest_deload") and prog["reasons"]
    assert call(a, "GET", "/progress/weekly", None, t)[1]["sessions"] == 3
    assert call(a, "GET", "/dashboard", None, t)[1]["plan_label"] == "experimental"


def test_s2_gym_intermediate_gets_loaded_exercises():
    a = build(); t = signup(a, "s2@ex.com", level="intermediate", goal="muscle_gain", days=4, minutes=120, equipment=["dumbbell", "bench", "barbell", "machine", "box", "band"])
    st, plan = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 200 and plan["result"]["structure"] == "upper_lower"
    assert any(a.store.catalog[c].candidate.equipment for c in codes(plan))
    assert call(a, "GET", "/safety/explain", None, t)[1]["items"]


def test_s3_back_history_without_pain_avoids_high_back_load_and_prefers_supportive():
    a = build(); t = signup(a, "s3@ex.com", level="intermediate", equipment=["dumbbell", "barbell", "bench", "box"], minutes=120)
    assert call(a, "POST", "/health/conditions", {"region": "lower_back", "problem_type": "diagnosed_injury", "status": "self_reported_symptom"}, t)[0] == 200
    st, plan = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 200
    cs = codes(plan)
    assert "barbell_back_squat" not in cs and "dumbbell_romanian_deadlift" not in cs                 # high lower-back loading excluded
    assert {"dead_bug", "bird_dog", "glute_bridge"} & set(cs)                                         # supportive (experimental tags) preferred
    ex = call(a, "GET", "/safety/explain", None, t)[1]
    rej = {i["code"]: i for i in ex["items"] if i["state"] == "rejected"}
    assert "barbell_back_squat" in rej and rej["barbell_back_squat"]["why"][0]["reason"] == "SAF-R301"


def test_s4_new_knee_pain_no_plan_with_guidance_then_explain():
    a = build(); t = signup(a, "s4@ex.com")
    assert call(a, "POST", "/workouts/generate", {}, t)[0] == 200
    st, body = call(a, "POST", "/health/pain-logs", {"region": "knee", "intensity": 6}, t)
    assert st == 200 and "treatment plans" in body["guidance"]["en"]
    st, body = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 409 and body["status"] == "BLOCKED" and "SAFETY:STOP_AND_REFER" in body["reasons"] and "SAF-R011" in body["reasons"]
    chat = call(a, "POST", "/ai/chat", {"message": "next session please"}, t)[1]
    assert chat["mode"] == "fixed" and ["safety", "STOP_AND_REFER"] in chat["trace"]               # AI cannot talk around Safety


def test_s5_red_flag_blocks_training_ai_and_nutrition():
    a = build(); t = signup(a, "s5@ex.com", red="chest_pain")
    assert call(a, "POST", "/workouts/generate", {}, t)[0] == 409
    assert call(a, "POST", "/ai/chat", {"message": "why this plan"}, t)[1]["mode"] == "fixed"
    n = call(a, "POST", "/nutrition/estimate", {"sex": "male", "height_cm": 180, "weight_kg": 80, "activity": "moderate",
                                                "screening": {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}}, t)[1]
    assert n["status"] == "BLOCKED" and n["tdee"] is None


def test_s6_eating_disorder_signal_refers_nutrition_but_training_continues():
    a = build(); t = signup(a, "s6@ex.com")
    n = call(a, "POST", "/nutrition/estimate", {"sex": "female", "height_cm": 165, "weight_kg": 60, "activity": "light",
                                                "screening": {"eating_disorder_risk": True, "medical_diet_needed": False, "pregnant_or_lactating": False}}, t)[1]
    assert n["status"] == "REFER" and n["macros"] is None
    assert call(a, "POST", "/workouts/generate", {}, t)[0] == 200


def test_s7_production_mode_never_serves_sample_content():
    a = build(allow=False); t = signup(a, "s7@ex.com")
    st, body = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 409 and "SAF-R013" in body["reasons"]
    assert call(a, "POST", "/ai/chat", {"message": "next session"}, t)[1]["mode"] == "fixed"


def test_s8_substitution_preserves_safety_and_versions():
    a = build(); t = signup(a, "s8@ex.com", days=1, equipment=["dumbbell", "bench", "box", "band"], minutes=90)
    plan = call(a, "POST", "/workouts/generate", {}, t)[1]
    target = next((c for c in codes(plan) if a.store.relations.get(c)), None)
    assert target
    r = call(a, "POST", "/workouts/plans/current/substitute", {"code": target, "reason": "equipment"}, t)[1]
    assert "version" in r or r.get("message") == "no_valid_alternative"
    vers = call(a, "GET", "/workouts/plans/current/versions", None, t)[1]["versions"]
    assert vers[0]["version"] == 1

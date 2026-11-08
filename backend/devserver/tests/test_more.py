import json
import re
from pathlib import Path
from app_services.store import InMemoryStore
from devserver.app import SCREENING, App
from devserver.demo_catalog import demo_catalog
from devserver.tests.test_api import call, make, onboard, _login
from safety_core.models import RuleSet


def test_password_reset_flow_and_no_enumeration():
    a = make(); _login(a, "u@ex.com")
    old = call(a, "POST", "/auth/login", {"email": "u@ex.com", "password": "Str0ngPassw0rd"})[1]["token"]
    r1 = call(a, "POST", "/auth/password-reset/request", {"email": "u@ex.com"})
    r2 = call(a, "POST", "/auth/password-reset/request", {"email": "ghost@ex.com"})
    assert r1[0] == r2[0] == 200 and r1[1] == r2[1] == {"accepted": True}
    tok = a.sent_resets[-1]
    assert call(a, "POST", "/auth/password-reset/confirm", {"token": tok, "new_password": "weak"})[0] == 422
    assert call(a, "POST", "/auth/password-reset/confirm", {"token": tok, "new_password": "N3wStrongPassword"})[0] in (200, 401)
    tok2 = None
    call(a, "POST", "/auth/password-reset/request", {"email": "u@ex.com"}); tok2 = a.sent_resets[-1]
    assert call(a, "POST", "/auth/password-reset/confirm", {"token": tok2, "new_password": "N3wStrongPassword"})[0] == 200
    assert call(a, "POST", "/auth/password-reset/confirm", {"token": tok2, "new_password": "N3wStrongPassword"})[0] == 401   # single use
    assert call(a, "GET", "/profile", None, old)[0] == 401                                                                      # sessions revoked
    assert call(a, "POST", "/auth/login", {"email": "u@ex.com", "password": "N3wStrongPassword"})[0] == 200


def test_profile_onboarding_consents_symptoms_versions():
    a = make(); t = onboard(a)
    assert call(a, "GET", "/profile", None, t)[1]["locale"] == "fa"
    assert call(a, "PATCH", "/profile", {"locale": "en"}, t)[1]["locale"] == "en"
    assert call(a, "PATCH", "/profile", {"locale": "xx"}, t)[0] == 422
    assert set(call(a, "GET", "/onboarding", None, t)[1]["steps_done"]) == {"basics", "goal", "schedule", "equipment"}
    docs = call(a, "GET", "/consents/documents")[1]["documents"]
    assert all(d["status"] == "draft_pending_legal_review" for d in docs)
    assert call(a, "POST", "/health/symptoms", {"region": "knee", "description": "تورم خفیف"}, t)[0] == 200
    assert call(a, "POST", "/health/symptoms", {"region": "knee", "description": ""}, t)[0] == 422
    assert call(a, "PATCH", "/health/conditions/0", {"status": "needs_reassessment"}, t)[0] == 200
    assert call(a, "PATCH", "/health/conditions/9", {"status": "needs_reassessment"}, t)[0] == 422
    call(a, "POST", "/onboarding/complete", {}, t)
    call(a, "POST", "/health/pain-logs", {"region": "wrist", "intensity": 0}, t)
    assert call(a, "GET", "/workouts/plans/current/versions", None, t)[0] == 404
    assert call(a, "GET", "/workouts/sessions", None, t)[1] == {"sessions": []}
    assert call(a, "GET", "/exercises/demo_squat_a/alternatives", None, t)[0] == 200
    assert call(a, "GET", "/exercises/none/alternatives", None, t)[0] == 404


def test_admin_listings_and_grants():
    a = make(); user = _login(a, "u@ex.com"); adm = _login(a, "a@ex.com", "admin"); pro = _login(a, "p@ex.com", "professional")
    assert call(a, "GET", "/admin/users", None, user)[0] == 403 and call(a, "GET", "/admin/exercises", None, user)[0] == 403
    assert call(a, "GET", "/admin/safety/rule-sets", None, user)[0] == 403
    users = call(a, "GET", "/admin/users", None, adm)[1]["users"]
    assert users and all(set(u) == {"id", "role", "plan"} for u in users)          # no email / health data for admins
    assert call(a, "GET", "/admin/exercises", None, adm)[0] == 200 and call(a, "GET", "/admin/safety/rule-sets", None, adm)[0] == 200
    assert call(a, "POST", "/admin/health-access-grants", {}, adm)[0] == 403
    pid = a.store.by_email["p@ex.com"]
    assert call(a, "POST", "/health/access-grants", {"professional_id": pid}, user)[0] == 200
    assert call(a, "POST", "/health/access-grants", {"professional_id": a.store.by_email["a@ex.com"]}, user)[0] == 404
    assert call(a, "GET", "/health/ready")[0] == 200


def test_every_openapi_endpoint_is_implemented():
    idx = json.loads((Path(__file__).resolve().parents[3] / "tools" / "api_index.json").read_text())
    a = make()
    def sample(path):                                   # fill path params with plausible values
        return re.sub(r"\{[^}]+\}", "x1", path)
    missing = []
    for _id, method, path, _tag in idx:
        if not any(m == method and rx.match("/api/v1" + sample(path)) for m, rx, _f, _a in a.routes):
            missing.append((_id, method, path))
    assert missing == [], [m[0] for m in missing]


def test_privacy_status_ai_chat_admin_create():
    from safety_core.models import REGIONS
    a = make(); t = onboard(a)
    rid = call(a, "POST", "/privacy/export", {}, t)[1]["request_id"]
    assert call(a, "GET", f"/privacy/requests/{rid}", None, t)[1]["status"] == "completed"
    other = _login(a, "o@ex.com")
    assert call(a, "GET", f"/privacy/requests/{rid}", None, other)[0] == 404
    # AI chat: free plan has no ai_chat -> 402 for LLM answers; safety/medical intents still get fixed text
    call(a, "POST", "/onboarding/complete", {}, t); call(a, "POST", "/workouts/generate", {}, t)
    assert ["rule_engine", "refuse:medical"] in call(a, "POST", "/ai/chat", {"message": "can you diagnose me"}, t)[1]["trace"]
    rule = call(a, "POST", "/ai/chat", {"message": "why this plan?"}, t)[1]
    assert rule["mode"] == "rule"                                   # deterministic answers are free: no quota, no LLM
    assert call(a, "POST", "/ai/chat", {"message": "tell me something motivating"}, t)[0] == 402
    a.sub.activate(a.store.by_email["u@ex.com"], "pro")
    r = call(a, "POST", "/ai/chat", {"message": "tell me something motivating"}, t)[1]
    assert r["mode"] == "ai" and r["labels"] == ["no_sources"]      # dev StubProvider
    prod = make(dev=False)
    assert prod.ai.provider.code == "unconfigured"
    adm = _login(a, "a@ex.com", "admin"); cm = _login(a, "c@ex.com", "content_admin")
    body = {"code": "my_ex", "movement_pattern": "core", "region_loads": {r: "none" for r in REGIONS}}
    assert call(a, "POST", "/admin/exercises", body, adm)[0] == 200
    assert call(a, "POST", "/admin/exercises", {**body, "code": "bad", "region_loads": {}}, adm)[0] == 422
    assert call(a, "POST", "/admin/exercises", {**body, "code": "z"}, t)[0] == 403
    assert "my_ex" not in call(a, "GET", "/exercises", None, t)[1]["items"]          # drafts never public


def test_nutrition_explain_progression_http():
    a = make(); t = onboard(a)
    n = {"sex": "male", "height_cm": 180, "weight_kg": 80, "activity": "moderate", "goal": "lose",
         "screening": {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}}
    st, body, _ = call(a, "POST", "/nutrition/estimate", n, t)
    assert st == 200 and body["status"] == "OK" and body["goal_adjustment"] == "disabled_pending_expert_review" and "not_medical_advice" in body["labels"]
    n2 = {**n, "screening": {**n["screening"], "eating_disorder_risk": True}}
    r2 = call(a, "POST", "/nutrition/estimate", n2, t)[1]
    assert r2["status"] == "REFER" and r2["tdee"] is None
    assert call(a, "POST", "/nutrition/meals", {"name": "Oats", "kcal": 350, "protein_g": 12}, t)[0] == 200
    assert call(a, "POST", "/nutrition/meals", {"name": ""}, t)[0] == 422
    assert call(a, "POST", "/nutrition/water", {"ml": 500}, t)[0] == 200
    sm = call(a, "GET", "/nutrition/summary", None, t)[1]
    assert sm["kcal"] == 350 and sm["water_ml"] == 500
    ex = call(a, "GET", "/safety/explain", None, t)[1]
    assert ex["status"] in ("ALLOW", "ALLOW_WITH_MODIFICATION") and ex["items"] and all("why" in i for i in ex["items"])
    call(a, "POST", "/onboarding/complete", {}, t)
    assert call(a, "GET", "/workouts/progression/demo_squat_a", None, t)[1]["action"] == "insufficient_data"

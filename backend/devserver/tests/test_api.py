import io
import json
import pytest
from app_services.store import InMemoryStore
from devserver.app import SCREENING, App
from devserver.demo_catalog import demo_catalog
from safety_core.models import RuleSet


def make(dev=True, allow=True):
    s = InMemoryStore(); s.catalog = demo_catalog()
    return App(s, RuleSet(version=0, status="t", screening_questions=SCREENING, allow_unreviewed_content=allow), dev)


def call(app, method, path, body=None, token=None, raw=None):
    data = raw if raw is not None else json.dumps(body or {}).encode()
    out = {}
    env = {"REQUEST_METHOD": method, "PATH_INFO": "/api/v1" + path, "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data)}
    if token: env["HTTP_AUTHORIZATION"] = "Bearer " + token
    res = b"".join(app(env, lambda st, h: out.update(status=int(st.split()[0]), headers=dict(h))))
    return out["status"], json.loads(res), out["headers"]


def onboard(app, age=30, days=3):
    call(app, "POST", "/auth/register", {"email": "u@ex.com", "password": "Str0ngPassw0rd"})
    t = call(app, "POST", "/auth/login", {"email": "u@ex.com", "password": "Str0ngPassw0rd"})[1]["token"]
    for step, d in [("basics", {"age": age}), ("goal", {"goal": "strength", "level": "beginner"}),
                    ("schedule", {"days_per_week": days, "session_minutes": 90}), ("equipment", {"equipment": []})]:
        assert call(app, "PUT", f"/onboarding/steps/{step}", d, t)[0] == 200
    call(app, "POST", "/consents", {"type": "health_data_processing"}, t)
    call(app, "POST", "/health/screening", {q: False for q in SCREENING}, t)
    return t


def test_full_http_flow():
    a = make(); t = onboard(a)
    assert call(a, "POST", "/onboarding/complete", {}, t)[0] == 200
    st, plan, hdr = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 200 and plan["result"]["status"] == "OK" and hdr["Cache-Control"] == "no-store"
    day = plan["result"]["days"][0]
    sid = call(a, "POST", "/workouts/sessions", {"day_name": day["name"]}, t)[1]["id"]
    assert call(a, "POST", f"/workouts/sessions/{sid}/logs", {"code": day["exercises"][0]["code"], "reps": 5, "load_kg": 40}, t)[0] == 200
    assert call(a, "POST", f"/workouts/sessions/{sid}/finish", {}, t)[0] == 200
    assert call(a, "GET", "/progress/weekly", None, t)[1]["volume_kg"] == 200.0
    assert call(a, "GET", "/workouts/current", None, t)[0] == 200


def test_minor_blocked_409_with_decision():
    a = make(); t = onboard(a, age=17)
    call(a, "POST", "/onboarding/complete", {}, t)
    st, body, _ = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 409 and body["error"] == "safety_blocked" and body["decision_id"] and "plan" not in body


def test_production_mode_blocks_unreviewed():
    a = make(allow=False); t = onboard(a); call(a, "POST", "/onboarding/complete", {}, t)
    st, body, _ = call(a, "POST", "/workouts/generate", {}, t)
    assert st == 409 and "SAF-R013" in body["reasons"]


def test_auth_required_and_errors():
    a = make()
    assert call(a, "GET", "/workouts/current")[0] == 401
    assert call(a, "GET", "/workouts/current", token="bad")[0] == 401
    assert call(a, "GET", "/nope")[0] == 404
    assert call(a, "POST", "/auth/login", {"email": "x@y.z", "password": "q"})[0] == 401
    assert call(a, "POST", "/auth/register", raw=b"{bad")[0] == 400
    assert call(a, "POST", "/auth/register", raw=b"[1]")[0] == 422
    assert call(a, "POST", "/auth/register", {"email": "bad", "password": "x"})[0] == 422
    assert call(a, "GET", "/health/live")[1] == {"status": "ok"}


def test_verify_disabled_outside_dev_and_requires_verification():
    a = make(dev=False)
    call(a, "POST", "/auth/register", {"email": "u@ex.com", "password": "Str0ngPassw0rd"})
    assert call(a, "POST", "/auth/login", {"email": "u@ex.com", "password": "Str0ngPassw0rd"})[0] == 401
    assert call(a, "POST", "/auth/verify", {"user_id": "usr-1"})[0] == 401


def test_cross_user_session_not_found():
    a = make(); t1 = onboard(a); call(a, "POST", "/onboarding/complete", {}, t1)
    p = call(a, "POST", "/workouts/generate", {}, t1)[1]
    sid = call(a, "POST", "/workouts/sessions", {"day_name": p["result"]["days"][0]["name"]}, t1)[1]["id"]
    call(a, "POST", "/auth/register", {"email": "o@ex.com", "password": "Str0ngPassw0rd"})
    t2 = call(a, "POST", "/auth/login", {"email": "o@ex.com", "password": "Str0ngPassw0rd"})[1]["token"]
    assert call(a, "POST", f"/workouts/sessions/{sid}/finish", {}, t2)[0] == 404


def test_logout_revokes_token():
    a = make(); t = onboard(a)
    assert call(a, "POST", "/auth/logout", {}, t)[0] == 200
    assert call(a, "GET", "/auth/sessions", None, t)[0] == 401


def test_pain_condition_means_no_plan():
    a = make(); t = onboard(a)
    call(a, "POST", "/health/conditions", {"region": "knee", "problem_type": "pain", "status": "self_reported_symptom", "active_pain": True}, t)
    call(a, "POST", "/onboarding/complete", {}, t)
    assert call(a, "POST", "/workouts/generate", {}, t)[0] == 409


def test_static_index_served():
    out = {}
    env = {"REQUEST_METHOD": "GET", "PATH_INFO": "/", "CONTENT_LENGTH": "0", "wsgi.input": io.BytesIO(b"")}
    body = b"".join(make()(env, lambda st, h: out.update(st=st, h=dict(h))))
    assert out["st"].startswith("200") and b'dir="rtl"' in body and "Content-Security-Policy" in out["h"]

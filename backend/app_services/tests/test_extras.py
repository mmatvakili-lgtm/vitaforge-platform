import json
import pytest
from app_services.errors import AuthFailed, NotFound, SafetyBlocked, ValidationFailed
from app_services.extras import ExtrasService
from app_services.tests.test_e2e import Env


@pytest.fixture
def e():
    env = Env(); env.x = ExtrasService(env.s, env.h, env.w, lambda: env.d); return env


def test_measurements_and_bmi(e):
    u = e.user()
    e.x.add_measurement(u, 80, 180)
    assert e.x.body_overview(u)["bmi"] == 24.7
    for kw in (dict(), dict(weight_kg=5), dict(height_cm=10)):
        with pytest.raises(ValidationFailed):
            e.x.add_measurement(u, **kw)
    assert e.x.body_overview("ghost")["bmi"] is None


def test_pain_log_stops_plan_and_gives_referral_guidance(e):
    u = e.user(); e.h.complete_onboarding(u)
    assert e.w.generate(u)
    r = e.x.log_pain(u, "lower_back", 6)
    assert "متخصص" in r["guidance"]["fa"] and "treatment plans" in r["guidance"]["en"]
    with pytest.raises(SafetyBlocked):                 # Path B: no program for new pain, referral instead
        e.w.generate(u)
    assert e.x.log_pain(u, "knee", 0)["guidance"] is None
    with pytest.raises(ValidationFailed):
        e.x.log_pain(u, "knee", 11)


def test_history_without_pain_gets_supportive_preference():
    from workout_engine import CatalogExercise
    import dataclasses
    env = Env(); env.x = ExtrasService(env.s, env.h, env.w, lambda: env.d)
    env.s.catalog["core_b"] = dataclasses.replace(env.s.catalog["core_b"], supports_regions=("lower_back",))
    u = env.user(days=3); env.h.add_condition(u, "lower_back", "diagnosed_injury", "self_reported_symptom", "self_reported", active_pain=False)
    env.h.complete_onboarding(u)
    r = env.w.generate(u)["result"]
    assert any("supportive" in x.reason for d in r.days for x in d.exercises)
    assert not any(c.startswith(("hinge",)) for c in r.codes)      # high lower-back load still blocked in caution region


def test_dashboard_and_health_profile(e):
    u = e.user(); e.h.complete_onboarding(u)
    assert e.x.dashboard(u)["has_plan"] is False
    e.w.generate(u)
    d = e.x.dashboard(u)
    assert d["has_plan"] and d["plan_version"] == 1 and d["plan_label"] == "experimental"
    e.h.add_condition(u, "knee", "pain", "self_reported_symptom")
    assert e.x.health_profile(u)["conditions"][0]["region"] == "knee"
    assert e.x.monthly_progress(u, 0, 10**6)["sessions"] == 0


def test_export_and_erasure(e):
    u = e.user(); e.h.complete_onboarding(u); e.w.generate(u)
    tok = e.id.login(e.s.users[u]["email"], "Str0ngPassw0rd") if e.s.users[u]["verified"] else None
    dump = e.x.export(u)
    assert "pw" not in json.dumps(dump, default=str) and dump["plans"][0]["version"] == 1
    e.x.erase(u)
    assert u not in e.s.users and u not in e.s.plans and not [c for c in e.s.consents if c["user"] == u]
    assert e.s.erasure_audit and u not in json.dumps(list(e.s.erasure_audit))
    with pytest.raises(NotFound):
        e.x.export(u)
    with pytest.raises(AuthFailed):
        e.id.authenticate(tok)

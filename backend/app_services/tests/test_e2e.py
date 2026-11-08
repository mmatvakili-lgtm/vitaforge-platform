import pytest
from app_services.errors import (AuthFailed, Conflict, Forbidden, Locked, NotFound, PreconditionRequired, SafetyBlocked,
                                 ValidationFailed)
from app_services.health_profile import CONSENT_HEALTH, HealthProfileService
from app_services.identity import IdentityService, hash_password, verify_password
from app_services.store import InMemoryStore
from app_services.workouts import WorkoutService
from safety_core import SafetyCore
from safety_core.models import RuleSet
from safety_core.tests.conftest import QUESTIONS, make_ex
from workout_engine import CatalogExercise
from workout_engine.tests.test_engine import catalog as make_catalog

PW = "Str0ngPassw0rd"


class Env:
    def __init__(self, published=False):
        self.t, self.d = 1000, 100
        self.s = InMemoryStore()
        self.s.catalog = {c.code: c for c in make_catalog()}
        self.s.relations = {"squat_a": [("squat_b", "alternative")], "squat_b": [("squat_a", "alternative")]}
        rs = RuleSet(version=1, status="t", screening_questions=QUESTIONS, allow_unreviewed_content=True,
                     clinical_content_published=published)
        self.id = IdentityService(self.s, lambda: self.t)
        self.h = HealthProfileService(self.s, lambda: self.d, QUESTIONS)
        self.w = WorkoutService(self.s, self.h, SafetyCore(rs), lambda: self.d)

    def user(self, age=30, consent=True, screening=False, days=3):
        uid = self.id.register(f"a{self.s.new_id('x')}@ex.com", PW)
        self.id.verify_email(uid)
        self.h.save_step(uid, "basics", {"age": age})
        self.h.save_step(uid, "goal", {"goal": "muscle_gain", "level": "beginner"})
        self.h.save_step(uid, "schedule", {"days_per_week": days, "session_minutes": 60})
        self.h.save_step(uid, "equipment", {"equipment": []})
        if consent:
            self.h.give_consent(uid, CONSENT_HEALTH, "v1")
        if screening is not None:
            self.h.answer_screening(uid, {q: bool(screening) for q in QUESTIONS})
        return uid


@pytest.fixture
def e():
    return Env()


def test_full_flow(e):
    uid = e.user()
    e.h.complete_onboarding(uid)
    v = e.w.generate(uid)
    assert v["version"] == 1 and v["result"].status == "OK" and v["result"].safety_decision_id
    day = v["result"].days[0].name
    sid = e.w.start_session(uid, day)
    e.w.log_set(uid, sid, v["result"].days[0].exercises[0].code, 8, 20, 7)
    e.w.log_set(uid, sid, v["result"].days[0].exercises[0].code, 8, 20, 7.5)
    e.w.finish(uid, sid)
    assert e.w.weekly_progress(uid, 95, 105) == {"sessions": 1, "sets": 2, "volume_kg": 320.0}
    assert e.w.weekly_progress(uid, 0, 10)["sessions"] == 0


def test_onboarding_needs_consent_and_steps(e):
    uid = e.user(consent=False)
    with pytest.raises(PreconditionRequired):
        e.h.complete_onboarding(uid)
    e.h.give_consent(uid, CONSENT_HEALTH, "v1")
    e.h.withdraw_consent(uid, CONSENT_HEALTH)
    with pytest.raises(PreconditionRequired):
        e.h.complete_onboarding(uid)
    u2 = e.id.register("b@ex.com", PW)
    with pytest.raises(ValidationFailed):
        e.h.complete_onboarding(u2)


def test_generate_requires_onboarding(e):
    with pytest.raises(PreconditionRequired):
        e.w.generate(e.user())


@pytest.mark.parametrize("kw", [dict(age=17), dict(consent=False), dict(screening=None)])
def test_safety_blocks_generation(e, kw):
    uid = e.user(**kw)
    if kw.get("consent") is False:
        e.h.give_consent(uid, CONSENT_HEALTH, "v1"); e.h.withdraw_consent(uid, CONSENT_HEALTH)
    e.s.profiles[uid]["complete"] = True
    with pytest.raises(SafetyBlocked):
        e.w.generate(uid)
    assert uid not in e.s.plans


def test_red_flag_blocks(e):
    uid = e.user(screening=True)
    e.s.profiles[uid]["complete"] = True
    with pytest.raises(SafetyBlocked) as x:
        e.w.generate(uid)
    assert x.value.status == "BLOCKED" and "SAF-R100" in x.value.reasons


def test_production_ruleset_unreviewed_blocks_everyone():
    e = Env(published=False)
    e.w.gate.rule_set = RuleSet(version=1, status="prod", screening_questions=QUESTIONS)
    uid = e.user(); e.h.complete_onboarding(uid)
    with pytest.raises(SafetyBlocked) as x:
        e.w.generate(uid)
    assert "SAF-R013" in x.value.reasons


def test_user_cannot_self_create_restriction_but_professional_can(e):
    uid = e.user()
    with pytest.raises(Forbidden):
        e.h.add_restriction(uid, "user", region="knee")
    e.h.add_restriction(uid, "professional", region="knee", max_loading="none")
    e.h.complete_onboarding(uid)
    r = e.w.generate(uid)["result"]
    assert not any(c.startswith(("squat", "lunge")) for c in r.codes)


def test_path_b_pain_gives_no_plan(e):
    uid = e.user()
    e.h.add_condition(uid, "knee", "pain", "self_reported_symptom", active_pain=True)
    e.h.complete_onboarding(uid)
    with pytest.raises(SafetyBlocked) as x:
        e.w.generate(uid)
    assert "NO_PROGRAM_PATH_B" in x.value.reasons or "SAF-R011" in x.value.reasons


def test_pregnancy_flag_blocks(e):
    uid = e.user(); e.h.add_out_of_scope(uid, "pregnancy"); e.h.complete_onboarding(uid)
    with pytest.raises(SafetyBlocked):
        e.w.generate(uid)


def test_substitute_safe_and_versioned(e):
    uid = e.user(days=1); e.h.complete_onboarding(uid)
    first = e.w.generate(uid)["result"]
    target = next(c for c in first.codes if c.startswith("squat"))
    other = "squat_b" if target == "squat_a" else "squat_a"
    assert other not in first.codes
    v = e.w.substitute(uid, target, "pain")
    assert v["version"] == 2 and v["pain_log"] and other in v["result"].codes and target not in v["result"].codes
    assert len(e.s.plans[uid]) == 2 and e.s.plans[uid][0]["result"] == first        # history immutable


def test_substitute_none_when_unsafe(e):
    uid = e.user(); e.h.add_restriction(uid, "admin", region="knee", max_loading="none"); e.h.complete_onboarding(uid)
    r = e.w.generate(uid)["result"]
    hinge = next(c for c in r.codes if c.startswith("hinge"))
    e.s.relations = {hinge: [("squat_a", "alternative"), ("squat_b", "regression")]}   # both blocked by the knee restriction
    assert e.w.substitute(uid, hinge, "other") is None
    assert len(e.s.plans[uid]) == 1
    with pytest.raises(ValidationFailed):
        e.w.substitute(uid, r.codes[0], "bogus")
    with pytest.raises(NotFound):
        e.w.substitute(uid, "nonexistent", "other")


def test_session_isolation_and_validation(e):
    a, b = e.user(), e.user()
    for u in (a, b): e.h.complete_onboarding(u); e.w.generate(u)
    sid = e.w.start_session(a, e.w.current(a)["result"].days[0].name)
    with pytest.raises(NotFound):
        e.w.log_set(b, sid, "x", 5, 10)
    with pytest.raises(ValidationFailed):
        e.w.log_set(a, sid, "x", 0, 10)
    with pytest.raises(ValidationFailed):
        e.w.log_set(a, sid, "x", 5, 10, rpe=11)
    e.w.finish(a, sid)
    with pytest.raises(Conflict):
        e.w.log_set(a, sid, "x", 5, 10)
    with pytest.raises(NotFound):
        e.w.start_session(a, "no-such-day")


# ---- identity
def test_identity_flow(e):
    uid = e.id.register("Me@Ex.com", PW)
    with pytest.raises(Conflict):
        e.id.register("me@ex.com", PW)
    with pytest.raises(AuthFailed):
        e.id.login("me@ex.com", PW)                         # unverified
    e.id.verify_email(uid)
    tok = e.id.login("me@ex.com", PW, "phone")
    assert e.id.authenticate(tok) == uid and len(e.id.list_sessions(uid)) == 1
    sid = e.id.list_sessions(uid)[0]["id"]
    e.id.revoke_session(uid, sid)
    with pytest.raises(AuthFailed):
        e.id.authenticate(tok)
    with pytest.raises(NotFound):
        e.id.revoke_session(uid, "ses-zzz")
    t2 = e.id.login("me@ex.com", PW); e.id.logout(t2)
    with pytest.raises(AuthFailed):
        e.id.authenticate(t2)


def test_lockout_and_same_error(e):
    uid = e.id.register("l@ex.com", PW); e.id.verify_email(uid)
    for _ in range(5):
        with pytest.raises(AuthFailed):
            e.id.login("l@ex.com", "wrong")
    with pytest.raises(Locked):
        e.id.login("l@ex.com", PW)
    e.t += 16 * 60
    assert e.id.login("l@ex.com", PW)
    with pytest.raises(AuthFailed):
        e.id.login("ghost@ex.com", "x")


@pytest.mark.parametrize("em,pw", [("bad", PW), ("a@b.co", "short1A"), ("a@b.co", "alllowercase1"), ("a@b.co", "NoDigitsHereAtAll")])
def test_register_validation(e, em, pw):
    with pytest.raises(ValidationFailed):
        e.id.register(em, pw)


def test_password_hash_not_plain():
    h = hash_password(PW)
    assert PW not in h and verify_password(PW, h) and not verify_password("x", h) and not verify_password(PW, "garbage")


def test_step_validation(e):
    u = e.id.register("v@ex.com", PW)
    for step, data in [("basics", {"age": "x"}), ("goal", {"goal": "x", "level": "beginner"}),
                       ("schedule", {"days_per_week": 9, "session_minutes": 60}), ("equipment", {"equipment": "a"}), ("zzz", {})]:
        with pytest.raises(ValidationFailed):
            e.h.save_step(u, step, data)
    for fn, args in [(e.h.add_condition, (u, "bad", "pain", "self_reported_symptom")), (e.h.add_out_of_scope, (u, "bad")),
                     (e.h.answer_screening, (u, {"unknown": True})), (e.h.answer_screening, (u, {QUESTIONS[0]: "yes"}))]:
        with pytest.raises(ValidationFailed):
            fn(*args)

"""Service-level behaviour added while making the API contract-conformant."""
import pytest

from app_services.errors import AuthFailed, Conflict, Gone, ValidationFailed
from app_services.extras import ExtrasService
from app_services.identity import SESSION_TTL, IdentityService
from app_services.more import MoreService
from app_services.store import InMemoryStore
from app_services.tests.test_e2e import PW, Env


def test_sessions_expire_after_the_ttl_and_record_last_seen():
    s, now = InMemoryStore(), [1000]
    ids = IdentityService(s, lambda: now[0])
    uid = ids.register("a@ex.com", PW); ids.verify_email(uid)
    tok = ids.login("a@ex.com", PW, "dev")
    now[0] += 60
    assert ids.authenticate(tok) == uid and ids.list_sessions(uid)[0]["seen"] == 1060
    now[0] = 1000 + SESSION_TTL - 1
    assert ids.authenticate(tok) == uid
    now[0] = 1000 + SESSION_TTL
    with pytest.raises(AuthFailed):
        ids.authenticate(tok)
    assert ids.list_sessions(uid) == []                       # expired sessions are not listed


def test_log_set_idempotency_pr_rule_and_finish_summary():
    e = Env(); uid = e.user(); e.h.complete_onboarding(uid); e.w.generate(uid)
    day = e.w.current(uid)["result"].days[0]
    sid = e.w.start_session(uid, day.name, now=0)
    code = day.exercises[0].code
    a, created = e.w.log_set(uid, sid, code, 8, 20, client_uuid="u1", set_no=1)
    b, created2 = e.w.log_set(uid, sid, code, 8, 20, client_uuid="u1", set_no=1)
    assert created and not created2 and a is b and len(e.s.workout_sessions[sid]["logs"]) == 1
    assert a["pr"] is False                                      # first set is a baseline
    c, _ = e.w.log_set(uid, sid, code, 8, 22.5, client_uuid="u2", set_no=2)
    d, _ = e.w.log_set(uid, sid, code, 8, 22.5, client_uuid="u3", set_no=3)
    assert c["pr"] is True and d["pr"] is False                  # equal to the best is not a record
    out = e.w.finish(uid, sid, now=1800, perceived_difficulty=6)
    assert out == {"volume_kg": 8 * 20 + 8 * 22.5 * 2, "sets_done": 3, "duration_min": 30}
    with pytest.raises(Conflict):
        e.w.finish(uid, sid, now=1900)
    with pytest.raises(Conflict):
        e.w.log_set(uid, sid, code, 5, 10, client_uuid="late")
    sid2 = e.w.start_session(uid, day.name)
    with pytest.raises(ValidationFailed):
        e.w.log_set(uid, sid2, code, 0, 10, client_uuid="z")     # zero reps without 'skipped' is invalid


def test_metric_bounds_units_and_overview():
    e = Env(); uid = e.user(); x = ExtrasService(e.s, e.h, e.w, lambda: 100)
    for bad in (("weight", 5, "kg"), ("weight", 70, "lb"), ("height", 175, "m"), ("body_fat_pct", 90, "%"), ("waist", True, "cm"), ("nope", 1, "cm")):
        with pytest.raises(ValidationFailed):
            x.add_metric(uid, bad[0], bad[1], bad[2], "measured")
    x.add_metric(uid, "height", 175, "cm", "measured"); x.add_metric(uid, "weight", 70, "kg", "measured"); x.add_metric(uid, "waist", 80, "cm", "measured")
    o = x.overview(uid)
    assert o["latest"] == {"height": 175, "weight": 70, "waist": 80} and o["bmi"]["value"] == 22.9 and o["whtr"]["value"] == 0.46


def test_reset_token_survives_a_weak_password_but_expires_and_is_single_use():
    e = Env(); uid = e.user(); now = [1000]
    m = MoreService(e.s, e.id, e.h, e.w, None, lambda: now[0])
    tok = m.request_reset(e.s.users[uid]["email"])
    with pytest.raises(ValidationFailed):
        m.confirm_reset(tok, "weakpass")
    m.confirm_reset(tok, "N3wStrongPassword")
    with pytest.raises(AuthFailed):
        m.confirm_reset(tok, "N3wStrongPassword")
    tok2 = m.request_reset(e.s.users[uid]["email"]); now[0] += 10**6
    with pytest.raises(Gone):
        m.confirm_reset(tok2, "N3wStrongPassword")

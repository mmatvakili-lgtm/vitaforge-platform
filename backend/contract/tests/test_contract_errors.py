"""Error responses: status declared in the spec, body is the Error envelope, behaviour is the intended one."""
import re
import time

import pytest

from contract.examples import example
from contract.harness import Harness, PASSWORD
from contract.scenarios import RANDOM_ID, happy_path
from contract.spec import contract
from devserver.app import SCREENING, pub

C = contract()
OPS = {o.id: o for o in C.ops}


def concrete(op, pid=RANDOM_ID):
    return re.sub(r"\{[^}]+\}", pid, op.path)


def body_for(op):
    return example(C, op.request_schema) if op.request_schema else None


@pytest.fixture()
def world():
    h = Harness()
    tokens = happy_path(h)
    h.log.clear()
    return h, tokens


def test_every_secured_operation_rejects_missing_and_garbage_credentials_with_401(world):
    h, _ = world
    for op in C.ops:
        if not op.secured:
            continue
        for tok in (None, "garbage-token"):
            r = h.call(op.method, concrete(op), body_for(op), token=tok)
            assert r.status == 401 and r.body["code"] == "auth_failed" and r.problems == [], (op.id, r.status, r.body)


def test_expired_and_revoked_sessions_are_401(world):
    h, tk = world
    t = h.login("exp@ex.com")
    for s in h.store.sessions.values():
        s["exp"] = int(time.time()) - 1
    assert h.call("GET", "/profile", token=t).status == 401
    t2 = h.login("rev2@ex.com")
    assert h.call("POST", "/auth/logout", token=t2).status == 200
    assert h.call("GET", "/profile", token=t2).status == 401


def test_unknown_ids_return_404_for_every_operation_that_takes_an_id(world):
    h, tk = world
    for op in C.ops:
        if not op.path_params or 404 not in op.declared or op.id in ("API-ONB-002",):
            continue
        tok = tk["admin"] if op.path.startswith("/admin") and op.id != "API-ADM-005" else tk["user"]
        if op.id == "API-ADM-005":
            tok = tk["reviewer"]
        if op.id == "API-ADM-003":
            tok = tk["content_admin"]
        r = h.call(op.method, concrete(op), body_for(op), token=tok)
        assert r.status == 404 and r.problems == [], (op.id, r.status, r.body)


def test_cross_user_resources_are_404_not_403(world):
    h, tk = world
    other = h.login("other@ex.com")
    sid = [e for e in h.store.workout_sessions][0]
    assert h.call("POST", f"/workouts/sessions/{pub('wks', sid)}/finish", {}, token=other).status == 404
    assert h.call("GET", f"/privacy/requests/{pub('prq', 'prq-1')}", token=other).status == 404


def test_health_operations_require_valid_consent_403(world):
    h, _ = world
    t = h.login("noconsent@ex.com")
    for op_id in ("API-HEALTH-001", "API-HEALTH-002", "API-HEALTH-003", "API-HEALTH-004", "API-HEALTH-005", "API-HEALTH-006", "API-HEALTH-007"):
        op = OPS[op_id]
        r = h.call(op.method, concrete(op), body_for(op), token=t)
        assert r.status == 403 and r.body["code"] == "consent_required" and r.problems == [], (op_id, r.status, r.body)


def test_admin_operations_forbid_ordinary_users_403(world):
    h, tk = world
    for op_id in ("API-ADM-001", "API-ADM-002", "API-ADM-004", "API-ADM-006", "API-ADM-007", "API-ADM-008"):
        op = OPS[op_id]
        pid = pub("plan_code", "free") if op_id == "API-ADM-008" else RANDOM_ID
        r = h.call(op.method, concrete(op, pid), body_for(op), token=tk["user"])
        assert r.status == 403 and r.problems == [], (op_id, r.status)
    # authorization precedes existence: no way to probe which ids exist
    assert h.call("POST", f"/admin/exercises/{RANDOM_ID}/transition", {"to_status": "retired"}, token=tk["user"]).status == 403
    assert h.call("POST", f"/admin/safety/rule-sets/{RANDOM_ID}/publish", {"confirm_sources_attached": True}, token=tk["user"]).status == 403
    # even a full admin cannot publish clinical rules
    assert h.call("POST", f"/admin/safety/rule-sets/{RANDOM_ID}/publish", {"confirm_sources_attached": True, "notes": "EXP-1"}, token=tk["admin"]).status == 403


def test_admin_cannot_grant_health_access_on_behalf_of_user(world):
    h, tk = world
    r = h.call("POST", "/admin/health-access-grants", {"grantee_id": RANDOM_ID, "subject_user_id": RANDOM_ID, "reason": "support ticket 1234", "duration_minutes": 10}, token=tk["admin"])
    assert r.status == 403 and r.problems == []


def test_conflicts_409(world):
    h, tk = world
    t = h.login("c1@ex.com")
    # onboarding incomplete / consent missing / no plan
    for n, a in [(1, {"age": 30}), (2, {"goal": "strength", "level": "beginner"}), (3, {"days_per_week": 3, "session_minutes": 60}), (4, {"equipment": []})]:
        h.call("PUT", f"/onboarding/steps/{n}", {"answers": a}, token=t)
    r = h.call("POST", "/onboarding/complete", token=t)
    assert r.status == 409 and r.body["code"] == "precondition_required" and r.problems == []
    r = h.call("POST", "/workouts/generate", {}, token=t)
    assert r.status == 409 and r.problems == []
    # finished session cannot take logs; cannot finish twice
    t1 = tk["user"]
    plan = h.call("GET", "/workouts/current", token=t1).body
    ss = h.call("POST", "/workouts/sessions", {"day_id": plan["days"][1]["day_id"]}, token=t1).body
    assert h.call("POST", f"/workouts/sessions/{ss['id']}/finish", {}, token=t1).status == 200
    assert h.call("POST", f"/workouts/sessions/{ss['id']}/finish", {}, token=t1).status == 409
    r = h.call("POST", f"/workouts/sessions/{ss['id']}/logs", {"client_uuid": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "exercise_id": plan["days"][1]["exercises"][0]["exercise_id"], "set_no": 1, "reps": 5}, token=t1)
    assert r.status == 409 and r.problems == []
    # lifecycle: draft -> published directly is a conflict; publishing an already published rule set is a conflict
    cr = h.call("POST", "/admin/exercises", {"stable_code": "x1", "movement_pattern": "core", "difficulty": "beginner"}, token=tk["content_admin"]).body
    r = h.call("POST", f"/admin/exercises/{cr['id']}/transition", {"to_status": "published"}, token=tk["reviewer"])
    assert r.status == 409 and r.problems == []
    h.store.rule_sets[9] = {"status": "published"}
    r = h.call("POST", f"/admin/safety/rule-sets/{pub('rs', 9)}/publish", {"confirm_sources_attached": True, "notes": "EXP-1"}, token=tk["reviewer"])
    assert r.status == 409 and r.problems == []


def test_incomplete_safety_tags_can_never_be_published(world):
    h, tk = world
    cr = h.call("POST", "/admin/exercises", {"stable_code": "untagged", "movement_pattern": "core", "difficulty": "beginner"}, token=tk["content_admin"]).body
    assert cr["review_status"] == "draft" and cr["safety_tags_complete"] is False
    h.call("POST", f"/admin/exercises/{cr['id']}/transition", {"to_status": "scientific_review"}, token=tk["content_admin"])
    ex_rev = h.login("exrev@ex.com", role="exercise_reviewer")
    h.call("POST", f"/admin/exercises/{cr['id']}/transition", {"to_status": "safety_review"}, token=ex_rev)
    r = h.call("POST", f"/admin/exercises/{cr['id']}/transition", {"to_status": "published"}, token=tk["reviewer"])
    assert r.status == 409 and r.problems == [] and "untagged" not in h.store.catalog


def test_gone_410_for_expired_codes_and_tokens():
    h = Harness(auto_verify=False)
    h.register("g@ex.com")
    uid = h.store.by_email["g@ex.com"]
    h.store.verification[uid]["exp"] = int(time.time()) - 1
    r = h.call("POST", "/auth/verify", {"identifier": "g@ex.com", "code": h.app.sent_codes["g@ex.com"]})
    assert r.status == 410 and r.problems == []
    h.call("POST", "/auth/password-reset/request", {"identifier": "g@ex.com"})
    for v in h.store.resets.values():
        v["exp"] = int(time.time()) - 1
    r = h.call("POST", "/auth/password-reset/confirm", {"token": h.app.sent_resets[-1], "new_password": "An0therStrongPass"})
    assert r.status == 410 and r.problems == []
    r = h.call("POST", "/auth/password-reset/confirm", {"token": "never-issued", "new_password": "An0therStrongPass"})
    assert r.status == 400 and r.problems == []
    assert h.call("POST", "/auth/verify", {"identifier": "g@ex.com", "code": "000000"}).status == 400


def test_semantic_validation_422_and_400(world):
    h, tk = world
    t = tk["user"]
    assert h.call("PUT", "/onboarding/steps/5", {"answers": {}}, token=t).status == 422          # step not built yet
    assert h.call("PUT", "/onboarding/steps/abc", {"answers": {}}, token=t).status == 400
    assert h.call("PUT", "/onboarding/steps/1", {"answers": {"age": 200}}, token=t).status == 422
    assert h.call("POST", "/workouts/generate", {"preferred_structure": "hybrid"}, token=t).status == 422
    assert h.call("POST", "/body/measurements", {"metric": "weight", "value": 5, "unit": "kg", "source": "measured"}, token=t).status == 422
    assert h.call("POST", "/body/measurements", {"metric": "weight", "value": 70, "unit": "lb", "source": "measured"}, token=t).status == 422
    assert h.call("POST", "/health/screening", {"screening_version": 2, "answers": {}}, token=t).status == 422
    assert h.call("POST", "/health/screening", {"screening_version": 1, "answers": {"nope": True}}, token=t).status == 422
    assert h.call("GET", "/exercises?page=0", token=t).status == 400
    assert h.call("GET", "/exercises?page_size=101", token=t).status == 400
    assert h.call("POST", "/subscriptions/checkout", {"plan_code": "nope", "billing_cycle": "monthly"}, token=t).status == 400
    assert h.call("POST", "/auth/register", {"password": PASSWORD, "date_of_birth": "1990-01-01"}).status == 422        # neither email nor phone
    assert h.call("POST", "/auth/register", {"phone": "+989121234567", "password": PASSWORD, "date_of_birth": "1990-01-01"}).status == 422
    for r in h.log[-12:]:
        assert r.problems == [], (r.path, r.problems)


def test_under_18_cannot_register_and_adult_boundary():
    h = Harness()
    from datetime import date
    t = date.today()
    minor = date(t.year - 17, 1, 1)
    r = h.call("POST", "/auth/register", {"email": "m@ex.com", "password": PASSWORD, "date_of_birth": minor.isoformat()})
    assert r.status == 422 and r.problems == [] and "m@ex.com" not in h.store.by_email
    adult = date(t.year - 18, t.month, t.day)
    assert h.call("POST", "/auth/register", {"email": "a@ex.com", "password": PASSWORD, "date_of_birth": adult.isoformat()}).status == 201
    future = date(t.year + 1, 1, 1)
    assert h.call("POST", "/auth/register", {"email": "f@ex.com", "password": PASSWORD, "date_of_birth": future.isoformat()}).status == 422


def test_register_does_not_reveal_existing_accounts():
    h = Harness()
    a = h.call("POST", "/auth/register", {"email": "dup@ex.com", "password": PASSWORD, "date_of_birth": "1990-01-01"})
    b = h.call("POST", "/auth/register", {"email": "dup@ex.com", "password": PASSWORD, "date_of_birth": "1990-01-01"})
    assert (a.status, a.body) == (b.status, b.body) == (201, {"message": "registered"})
    h.call("POST", "/auth/password-reset/request", {"identifier": "nobody@ex.com"})
    assert h.call("POST", "/auth/password-reset/request", {"identifier": "dup@ex.com"}).body == h.log[-2].body


def test_login_failures_401_and_lockout_423():
    h = Harness()
    h.register("l@ex.com")
    r = h.call("POST", "/auth/login", {"identifier": "l@ex.com", "password": "wrong-password-1"})
    assert r.status == 401 and r.problems == []
    assert h.call("POST", "/auth/login", {"identifier": "ghost@ex.com", "password": "wrong-password-1"}).body["code"] == r.body["code"]
    for _ in range(5):
        h.call("POST", "/auth/login", {"identifier": "l@ex.com", "password": "wrong-password-1"})
    r = h.call("POST", "/auth/login", {"identifier": "l@ex.com", "password": PASSWORD})
    assert r.status == 423 and r.problems == []                       # correct password is refused while locked


def test_needs_content_422_carries_reasons_and_never_an_invented_plan():
    h = Harness()
    t = h.login("n@ex.com")
    h.onboard(t)
    h.call("POST", "/onboarding/complete", token=t)
    keep = next(iter(h.store.catalog))
    h.store.catalog = {keep: h.store.catalog[keep]}
    r = h.call("POST", "/workouts/generate", {}, token=t)
    assert r.status == 422 and r.body["code"] == "needs_content" and r.body["details"]["reasons"] and r.problems == []
    assert "plan" not in r.body


def test_safety_blocks_return_200_decision_with_null_plan():
    h = Harness()
    # minor (age 17 declared in onboarding)
    t = h.login("minor@ex.com"); h.onboard(t, age=17); h.call("POST", "/onboarding/complete", token=t)
    r = h.call("POST", "/workouts/generate", {}, token=t)
    assert r.status == 200 and r.body["plan"] is None and r.body["decision"]["status"] not in ("ALLOW", "ALLOW_WITH_MODIFICATION") and r.problems == []
    assert any(x["code"] == "SAF-R001" for x in r.body["decision"]["reasons"])
    # warning symptom -> refer
    t2 = h.login("rf@ex.com"); h.onboard(t2)
    h.call("POST", "/health/screening", {"screening_version": 1, "answers": {"chest_pain": True, **{q: False for q in SCREENING if q != "chest_pain"}}}, token=t2)
    h.call("POST", "/onboarding/complete", token=t2)
    r = h.call("POST", "/workouts/generate", {}, token=t2)
    assert r.body["plan"] is None and r.body["decision"]["status"] == "STOP_AND_REFER" and r.body["decision"]["referral"]["urgency"] in ("urgent", "non_urgent")
    # active pain logged -> no plan
    t3 = h.login("pain@ex.com"); h.onboard(t3); h.call("POST", "/onboarding/complete", token=t3)
    assert h.call("POST", "/health/pain-logs", {"region": "knee", "intensity": 7, "timing": "during"}, token=t3).status == 201
    r = h.call("POST", "/workouts/generate", {}, token=t3)
    assert r.body["plan"] is None and r.problems == []


def test_production_mode_never_serves_unreviewed_content():
    h = Harness(dev=False, allow=False)
    t = h.login("p@ex.com")
    h.onboard(t); h.call("POST", "/onboarding/complete", token=t)
    r = h.call("POST", "/workouts/generate", {}, token=t)
    assert r.status == 200 and r.body["plan"] is None and r.body["decision"]["status"] == "ERROR_FAILSAFE" and r.problems == []
    assert h.call("POST", "/auth/verify", {"identifier": "p@ex.com", "code": "123456"}).status in (400, 410)


def test_payment_and_ai_quota_statuses(world):
    h, tk = world
    t = h.login("free@ex.com"); h.onboard(t)
    r = h.call("POST", "/subscriptions/checkout", {"plan_code": "pro", "billing_cycle": "yearly"}, token=t)
    assert r.status == 501 and r.body["code"] == "feature_unavailable" and r.problems == []
    r = h.call("POST", "/ai/chat", {"purpose": "general", "message": "hello"}, token=t)
    assert r.status in (200, 402) and r.problems == []
    if r.status == 200:
        assert r.body["mode"] in ("llm", "rule_based_fallback")


def test_cookie_auth_requires_csrf_but_bearer_does_not():
    h = Harness()
    h.register("cs@ex.com")
    r = h.call("POST", "/auth/login", {"identifier": "cs@ex.com", "password": PASSWORD})
    sid = re.search(r"sessionid=([^;]+)", r.headers["Set-Cookie"]).group(1)
    csrf = re.search(r"csrftoken=([^;]+)", r.headers["Set-Cookie"]).group(1)
    cookie = {"Cookie": f"sessionid={sid}; csrftoken={csrf}"}
    assert h.call("GET", "/profile", headers=cookie).status == 200                               # safe method: no CSRF header needed
    assert h.call("PATCH", "/profile", {"display_name": "x"}, headers=cookie, check=False).status == 403
    assert h.call("PATCH", "/profile", {"display_name": "x"}, headers={**cookie, "X-CSRFToken": "wrong"}, check=False).status == 403
    assert h.call("PATCH", "/profile", {"display_name": "x"}, headers={**cookie, "X-CSRFToken": csrf}).status == 200
    assert h.call("PATCH", "/profile", {"display_name": "y"}, token=sid).status == 200


def test_malformed_and_oversized_bodies():
    h = Harness()
    assert h.call("POST", "/auth/login", raw=b"{not json").status == 400
    assert h.call("POST", "/auth/login", raw=b'["x"]').status == 400
    big = h.call("POST", "/auth/login", raw=b"{" + b" " * 200_000 + b"}", check=False)
    assert big.status == 413 and set(big.body) >= {"code", "message", "request_id"}
    assert h.call("GET", "/nope").status == 404 and h.call("PUT", "/health/live").status == 405


def test_error_bodies_never_echo_submitted_secrets_or_internals():
    h = Harness()
    secret = "SuperSecret-Value-123"
    r = h.call("POST", "/auth/login", {"identifier": 12345, "password": secret})
    assert r.status == 400 and secret not in str(r.body) and r.body["details"]["fields"][0] == {"path": "identifier", "rule": "type"}
    r = h.call("POST", "/auth/register", {"email": "e@ex.com", "password": secret, "date_of_birth": "nope"})
    assert secret not in str(r.body) and "Traceback" not in str(r.body)

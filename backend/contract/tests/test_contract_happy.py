from contract.harness import Harness
from contract.scenarios import happy_path
from contract.spec import contract

C = contract()


def test_every_operation_returns_its_declared_success_status_with_a_conforming_body():
    h = Harness()
    happy_path(h)
    assert h.problems == [], h.problems[:5]
    ok = {e.op.id for e in h.log if e.op and e.status == e.op.success_status}
    # SUB-003 (payments disabled) and ADM-007 (grants are user-initiated) are intentionally not 2xx; asserted below.
    assert {o.id for o in C.ops} - ok == {"API-SUB-003", "API-ADM-007"}
    by = {e.op.id: e for e in h.log if e.op}
    assert by["API-SUB-003"].status == 501 and by["API-ADM-007"].status == 403


def test_success_bodies_are_not_trivially_empty():
    h = Harness()
    happy_path(h)
    by = {}
    for e in h.log:
        if e.op and e.status == e.op.success_status:
            by.setdefault(e.op.id, e)
    plan = by["API-WO-001"].body["plan"]
    assert plan["days"] and all(d["exercises"] and all(x["sets"] for x in d["exercises"]) for d in plan["days"])
    assert by["API-WO-001"].body["decision"]["status"] in ("ALLOW", "ALLOW_WITH_MODIFICATION")
    assert by["API-BODY-001"].body["bmi"] == {"value": 22.9, "label": "screening_index"}
    assert by["API-BODY-001"].body["whtr"]["label"] == "screening_index"
    assert by["API-LOG-002"].body["personal_record"] is False           # first set of an exercise is a baseline
    second = [e for e in h.log if e.op and e.op.id == "API-LOG-002"][1]
    assert second.body["personal_record"] is True                      # 25 kg beats 20 kg
    assert by["API-LOG-003"].body["sets_done"] == 2 and by["API-LOG-003"].body["volume_kg"] == 8 * 20 + 8 * 25
    assert by["API-EX-001"].body["count"] >= 1 and by["API-EX-001"].body["results"]


def test_login_sets_httponly_cookie_and_returns_no_token_in_body():
    h = Harness()
    h.register("c@ex.com")
    h.verify_by_mail("c@ex.com")
    r = h.call("POST", "/auth/login", {"identifier": "c@ex.com", "password": "Str0ngPassw0rd"})
    cookies = r.headers["Set-Cookie"]
    assert "sessionid=" in cookies and "HttpOnly" in cookies and "SameSite=Lax" in cookies and "csrftoken=" in cookies
    assert "token" not in r.body and set(r.body) <= {"user_id", "expires_at", "onboarding_status"}

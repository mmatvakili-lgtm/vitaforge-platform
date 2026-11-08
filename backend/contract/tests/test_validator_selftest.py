"""The validator itself must reject wrong payloads; otherwise 'conformance' would be meaningless."""
import pytest

from contract.spec import contract

C = contract()
op = {o.id: o for o in C.ops}


def probs(op_id, status, body, ct="application/json"):
    return C.check_response(op[op_id], status, body, ct)


GOOD_DECISION = {"decision_id": "11111111-2222-4333-8444-555555555555", "status": "ALLOW"}


def test_accepts_valid_and_nullable():
    assert probs("API-WO-001", 200, {"decision": GOOD_DECISION, "plan": None}) == []
    assert probs("API-SYS-001", 200, {"message": "ok"}) == []


@pytest.mark.parametrize("body", [
    {"plan": None},                                                          # required decision missing
    {"decision": {**GOOD_DECISION, "status": "MAYBE"}, "plan": None},        # enum
    {"decision": {**GOOD_DECISION, "decision_id": "not-a-uuid"}},            # format uuid
    {"decision": {**GOOD_DECISION, "extra": 1}},                             # additionalProperties
    {"decision": {**GOOD_DECISION, "rule_set_version": "1"}},                # type
    {"decision": {**GOOD_DECISION, "evaluated_at": "2026-01-01 10:00:00"}},  # format date-time
    {"decision": GOOD_DECISION, "plan": {"plan_id": "x"}},                   # nested oneOf/required
])
def test_rejects_invalid_response_bodies(body):
    assert probs("API-WO-001", 200, body)


def test_rejects_undeclared_status_and_wrong_content_type_and_error_envelope():
    assert any("not declared" in p for p in probs("API-SYS-001", 500, {"code": "x", "message": "y"}))
    assert probs("API-SYS-001", 200, {"message": "ok"}, "text/html")
    assert probs("API-AUTH-003", 401, {"error": "auth_failed"})              # legacy envelope must fail
    assert probs("API-AUTH-003", 401, {"code": "auth_failed", "message": "m"}) == []


def test_const_and_number_constraints_and_bool_not_integer():
    assert C.errors({"$ref": "#/components/schemas/DeleteRequest"}, {"password": "p", "confirm": False})
    assert C.errors({"$ref": "#/components/schemas/MeasurementRequest"}, {"metric": "weight", "value": 0, "unit": "kg", "source": "measured"})   # exclusiveMinimum 0
    assert C.errors({"$ref": "#/components/schemas/PainLogRequest"}, {"region": "knee", "intensity": True, "timing": "after"})                    # bool is not integer


def test_request_validation_matches_spec_required_and_formats():
    r = {"$ref": "#/components/schemas/RegisterRequest"}
    ok = {"email": "a@b.co", "password": "x" * 10, "date_of_birth": "1990-01-01"}
    assert C.errors(r, ok) == []
    assert C.errors(r, {**ok, "password": "short"})                      # minLength
    assert C.errors(r, {**ok, "date_of_birth": "1990-13-01"})            # format date
    assert C.errors(r, {**ok, "phone": "09121234567"})                   # pattern
    assert C.errors(r, {k: v for k, v in ok.items() if k != "date_of_birth"})

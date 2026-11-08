"""Request-side contract: schema-valid payloads pass the schema layer; every schema-invalid mutation is rejected before any handler runs."""
import re

import pytest

from contract.examples import example, mutations
from contract.harness import Harness
from contract.scenarios import RANDOM_ID, happy_path
from contract.spec import contract

C = contract()
WITH_BODY = [o for o in C.ops if o.request_schema]


@pytest.fixture(scope="module")
def world():
    h = Harness()
    tk = happy_path(h)
    return h, tk


def token_for(op, tk):
    if op.path.startswith("/admin"):
        return tk["reviewer"] if op.id == "API-ADM-005" else tk["admin"]
    return None if not op.secured else tk["user"]


def concrete(op):
    return re.sub(r"\{[^}]+\}", RANDOM_ID, op.path)


def test_generated_examples_are_themselves_schema_valid():
    for op in WITH_BODY:
        assert C.check_request(op, example(C, op.request_schema)) == [], op.id


@pytest.mark.parametrize("op", WITH_BODY, ids=lambda o: o.id)
def test_schema_valid_payload_is_not_rejected_by_the_schema_layer(world, op):
    h, tk = world
    r = h.call(op.method, concrete(op), example(C, op.request_schema), token=token_for(op, tk))
    rejected_by_schema = r.status in (400, 422) and r.body.get("code") == "validation_failed" and "fields" in r.body.get("details", {})
    assert not rejected_by_schema, (op.id, r.body)
    assert r.problems == [], (op.id, r.problems)


@pytest.mark.parametrize("op", WITH_BODY, ids=lambda o: o.id)
def test_every_schema_invalid_mutation_is_rejected_with_a_declared_validation_status(world, op):
    h, tk = world
    muts = mutations(C, op.request_schema)
    assert muts, op.id
    for name, body in muts:
        r = h.call(op.method, concrete(op), body, token=token_for(op, tk), label=name)
        assert r.status in (400, 422) and r.status in op.declared, (op.id, name, r.status, r.body)
        assert r.body["code"] == "validation_failed" and r.body["details"]["fields"], (op.id, name, r.body)
        assert r.problems == [], (op.id, name, r.problems)
        for f in r.body["details"]["fields"]:
            assert set(f) == {"path", "rule"}                          # never echoes the submitted value


def test_validation_precedes_side_effects(world):
    h, tk = world
    n = len(h.store.users)
    h.call("POST", "/auth/register", {"email": "bad@ex.com", "password": "short", "date_of_birth": "1990-01-01"})
    assert len(h.store.users) == n and "bad@ex.com" not in h.store.by_email
    cons = len(h.store.consents)
    h.call("POST", "/consents", {"document_id": "nope", "granted": True}, token=tk["user"])
    assert len(h.store.consents) == cons


def test_mutation_count_is_substantial():
    assert sum(len(mutations(C, o.request_schema)) for o in WITH_BODY) > 200

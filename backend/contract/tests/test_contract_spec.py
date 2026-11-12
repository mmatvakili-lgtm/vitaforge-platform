import json
from pathlib import Path

from contract.spec import contract
from devserver.app import App
from contract.harness import Harness

C = contract()


def test_spec_uses_only_constructs_valid_for_its_declared_version():
    assert C.spec_dialect_problems() == []


def test_every_operation_has_a_handler_and_route_and_matches_api_index():
    h = Harness()                                        # App.__init__ raises if any spec operation lacks a handler
    routed = {(m, rx.pattern) for m, rx, _f, _a, op in h.app.routes if op}
    assert len(routed) == len(C.ops) == 75
    idx = json.loads((Path(__file__).resolve().parents[3] / "tools" / "api_index.json").read_text(encoding="utf-8"))
    assert sorted(i[0] for i in idx) == sorted(o.id for o in C.ops)


def test_every_response_has_a_schema_and_errors_use_the_error_envelope():
    for op in C.ops:
        for st, spec in op.raw["responses"].items():
            ref = spec["content"]["application/json"]["schema"]
            if not st.startswith("2"):
                assert ref == {"$ref": "#/components/schemas/Error"}, (op.id, st)
        assert op.success_status in (200, 201, 202)


def test_every_operation_with_input_can_report_invalid_input():
    """Regression for a spec gap found by this suite: AUTH-005, LOG-003, AI-001, ADM-005 (body) and EX-001, LOG-004 (query)
    declared neither 400 nor 422, so a conforming server had no legal way to reject bad input."""
    for op in C.ops:
        has_input = op.request_schema is not None or any(p.get("in") == "query" for p in op.raw.get("parameters", []))
        if has_input:
            assert 400 in op.declared or 422 in op.declared, op.id

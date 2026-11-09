import dataclasses
import pytest
from safety_core import evaluate
from safety_core import engine as E
from safety_core.explain import TEXT, explain
from safety_core.models import DecisionStatus as S, Restriction
from .conftest import make_ex


def test_equipment_and_level_reasons_explained(req, rules):
    cands = (make_ex("a", equipment=("barbell",)), make_ex("b", difficulty="advanced"), make_ex("c"), make_ex("d", equipment=("bodyweight",)))
    d = evaluate(req(candidates=cands, equipment=("dumbbell",), user_level="beginner"), rules)
    assert d.allowed_codes == ("c", "d") and d.status == S.ALLOW_WITH_MODIFICATION
    ex = explain(d, "en")
    by = {i["code"]: i for i in ex["items"]}
    assert by["a"]["why"][0]["reason"] == E.R_EQUIPMENT and "equipment" in by["a"]["why"][0]["text"]
    assert by["b"]["why"][0]["reason"] == E.R_LEVEL and by["c"]["state"] == "allowed"


def test_unconstrained_by_default(req, rules):
    d = evaluate(req(candidates=(make_ex("a", equipment=("barbell",), difficulty="advanced"),)), rules)
    assert d.allowed_codes == ("a",)


def test_bad_level_failsafe(req, rules):
    assert evaluate(req(user_level="god"), rules).status == S.ERROR_FAILSAFE


def test_every_emitted_reason_code_has_text():
    import re, pathlib
    src = pathlib.Path(E.__file__).read_text(encoding="utf-8")
    codes = set(re.findall(r'"(SAF-R\d{3})"', src))
    assert codes <= set(TEXT), codes - set(TEXT)


def test_explain_structure_and_languages(req, rules):
    d = evaluate(req(restrictions=(Restriction(exercise_code="curl"),)), rules)
    fa, en = explain(d, "fa"), explain(d, "en")
    rej = [i for i in fa["items"] if i["state"] == "rejected"][0]
    assert rej["code"] == "curl" and rej["why"][0]["text"] != en["items"][0]["why"][0]["text"]
    assert fa["decision_id"] == d.decision_id and fa["rule_set_version"] == rules.version
    assert explain(evaluate(req(age_years=10), rules))["overall"][0]["reason"] == "SAF-R001"
    assert explain(evaluate(req(age_years=None), rules))["questions"] == ["age"]

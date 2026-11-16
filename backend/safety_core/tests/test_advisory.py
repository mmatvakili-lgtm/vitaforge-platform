"""Advisory (warn-not-block) posture, DEC-ADVISORY. Strict behaviour is covered by test_engine.py and stays unchanged."""
import dataclasses

from safety_core import engine as E
from safety_core import evaluate, validate_plan
from safety_core.models import Condition, DecisionStatus as S, OutOfScopeFlag
from .conftest import QUESTIONS, make_ex


def adv(rules):
    return dataclasses.replace(rules, advisory_mode=True)


def test_red_flag_strict_stops_but_advisory_gives_plan_with_urgent_referral(req, rules):
    r = req(red_flag_answers={"chest_pain": True, "fainting": False})
    assert evaluate(r, rules).status == S.STOP_AND_REFER
    d = evaluate(r, adv(rules))
    assert d.status == S.ALLOW_WITH_MODIFICATION and set(d.allowed_codes) == {"squat", "curl"}
    assert "ADVISORY_REFER" in d.flags and E.R_ADVISORY in d.reasons and E.R_RED_FLAG in d.reasons
    assert d.referral_urgency in ("urgent", "non_urgent")


def test_pregnancy_is_a_warning_in_advisory(req, rules):
    r = req(out_of_scope_flags=(OutOfScopeFlag("pregnancy"),))
    assert evaluate(r, rules).status == S.BLOCK_OUT_OF_SCOPE
    d = evaluate(r, adv(rules))
    assert d.status.permits_content and E.R_PREGNANCY in d.reasons


def test_minor_and_consent_and_missing_data_still_stop_in_advisory(req, rules):
    a = adv(rules)
    assert evaluate(req(age_years=17), a).status == S.BLOCK_OUT_OF_SCOPE
    assert evaluate(req(consent_health_valid=False), a).status == S.BLOCK_CONSENT
    assert evaluate(req(age_years=None), a).status == S.NEEDS_INFO


def test_unanswered_screening_does_not_block_in_advisory(req, rules):
    r = req(red_flag_answers={})
    assert evaluate(r, rules).status == S.NEEDS_INFO
    assert evaluate(r, adv(rules)).status.permits_content


def test_contraindicated_item_is_cautioned_not_removed_in_advisory(req, rules):
    cond = Condition(region="knee", problem_type="pain", status="self_reported_symptom")
    r = req(conditions=(cond,), candidates=(make_ex("a", contraindications=(("x", "knee"),)), make_ex("b")))
    assert "a" not in evaluate(r, rules).allowed_codes
    item = {i.code: i for i in evaluate(r, adv(rules)).per_item}["a"]
    assert item.allowed and item.caution and E.R_CONTRA in item.reasons


def test_validate_plan_consistent_under_advisory(req, rules):
    r = req(red_flag_answers={"chest_pain": True, "fainting": False})
    a = adv(rules)
    ok, v = validate_plan(("squat",), evaluate(r, a), r, a)
    assert ok, v

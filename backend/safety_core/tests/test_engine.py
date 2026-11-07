import dataclasses
import pytest
from safety_core import SafetyCore, evaluate, find_alternatives, validate_plan
from safety_core import engine as E
from safety_core.models import (ClinicalRule, Condition, DecisionStatus as S, OutOfScopeFlag, Restriction, RuleSet)
from .conftest import QUESTIONS, make_ex


# ---- ST: consent / age
@pytest.mark.parametrize("age,exp", [(17, S.BLOCK_OUT_OF_SCOPE), (18, S.ALLOW), (0, S.BLOCK_OUT_OF_SCOPE)])
def test_age_boundary(req, rules, age, exp):
    assert evaluate(req(age_years=age), rules).status == exp


def test_age_minor_reason(req, rules):
    assert E.R_AGE in evaluate(req(age_years=17), rules).reasons


def test_negative_age_failsafe(req, rules):
    assert evaluate(req(age_years=-1), rules).status == S.ERROR_FAILSAFE


def test_consent_false_blocks(req, rules):
    d = evaluate(req(consent_health_valid=False), rules)
    assert d.status == S.BLOCK_CONSENT and not d.allowed_codes


def test_missing_age_consent_needs_info(req, rules):
    d = evaluate(req(age_years=None, consent_health_valid=None), rules)
    assert d.status == S.NEEDS_INFO and set(d.required_questions) == {"age", "consent_health"}


# ---- out of scope
def test_pregnancy_blocks(req, rules):
    d = evaluate(req(out_of_scope_flags=(OutOfScopeFlag("pregnancy"),)), rules)
    assert d.status == S.BLOCK_OUT_OF_SCOPE and E.R_PREGNANCY in d.reasons


def test_inactive_flag_ignored(req, rules):
    assert evaluate(req(out_of_scope_flags=(OutOfScopeFlag("pregnancy", active=False),)), rules).status == S.ALLOW


# ---- red flags
def test_red_flag_positive_stops(req, rules):
    d = evaluate(req(red_flag_answers={"chest_pain": True, "fainting": False}), rules)
    assert d.status == S.STOP_AND_REFER and not d.allowed_codes


def test_red_flag_unanswered_needs_info(req, rules):
    d = evaluate(req(red_flag_answers={"chest_pain": False, "fainting": None}), rules)
    assert d.status == S.NEEDS_INFO and d.required_questions == ("fainting",)


def test_red_flag_beats_conditions(req, rules):
    d = evaluate(req(red_flag_answers={"chest_pain": True, "fainting": False},
                     conditions=(Condition("knee", "pain", "no_known_limitation"),)), rules)
    assert d.status == S.STOP_AND_REFER


def test_urgent_status_stops(req, rules):
    d = evaluate(req(conditions=(Condition("knee", "pain", "needs_urgent_referral"),)), rules)
    assert d.status == S.STOP_AND_REFER and d.referral_urgency == "urgent"


# ---- clinical content gate
def test_unreviewed_content_failsafe_in_production(req):
    rs = RuleSet(version=1, status="prod", screening_questions=QUESTIONS)
    d = evaluate(req(), rs)
    assert d.status == S.ERROR_FAILSAFE and E.R_CONTENT_UNREVIEWED in d.reasons and not d.allowed_codes


def test_published_content_allows(req):
    rs = RuleSet(version=1, status="prod", screening_questions=QUESTIONS, clinical_content_published=True)
    assert evaluate(req(), rs).status == S.ALLOW


# ---- restrictions
def test_restriction_blocks_region_load(req, rules):
    cands = (make_ex("deadlift", {"lower_back": "high"}), make_ex("curl", pattern="curl"))
    d = evaluate(req(candidates=cands, restrictions=(Restriction(region="lower_back", max_loading="low"),),
                     conditions=(Condition("lower_back", "diagnosed_injury", "active_professional_restriction", "professional"),)), rules)
    assert d.status == S.ALLOW_WITH_MODIFICATION and d.allowed_codes == ("curl",)


def test_restriction_allows_up_to_max(req, rules):
    cands = (make_ex("goodmorning", {"lower_back": "low"}),)
    d = evaluate(req(candidates=cands, restrictions=(Restriction(region="lower_back", max_loading="low"),)), rules)
    assert d.allowed_codes == ("goodmorning",)


def test_restriction_default_none_blocks_any_load(req, rules):
    cands = (make_ex("a", {"knee": "low"}),)
    d = evaluate(req(candidates=cands, restrictions=(Restriction(region="knee"),)), rules)
    assert d.status == S.RESTRICT and not d.allowed_codes


def test_restriction_by_pattern_and_code(req, rules):
    d = evaluate(req(restrictions=(Restriction(movement_pattern="squat"),)), rules)
    assert d.allowed_codes == ("curl",)
    d = evaluate(req(restrictions=(Restriction(exercise_code="curl"),)), rules)
    assert d.allowed_codes == ("squat",)


def test_expired_restriction_still_applies_and_flags(req, rules):
    d = evaluate(req(today_ordinal=10, restrictions=(Restriction(exercise_code="curl", valid_until_ordinal=5),)), rules)
    assert d.allowed_codes == ("squat",) and "REASSESSMENT_RECOMMENDED" in d.flags and E.R_EXPIRED_RESTRICTION in d.reasons


def test_professional_condition_without_structured_restriction_blocks_region(req, rules):
    cands = (make_ex("a", {"knee": "low"}), make_ex("b"))
    d = evaluate(req(candidates=cands, conditions=(Condition("knee", "diagnosed_injury", "active_professional_restriction", "professional"),)), rules)
    assert d.allowed_codes == ("b",) and E.R_UNANALYSABLE in d.reasons


def test_needs_reassessment_blocks_and_flags(req, rules):
    cands = (make_ex("a", {"knee": "low"}), make_ex("b"))
    d = evaluate(req(candidates=cands, conditions=(Condition("knee", "pain", "needs_reassessment"),)), rules)
    assert d.allowed_codes == ("b",) and "REASSESSMENT_RECOMMENDED" in d.flags


def test_self_reported_caution_region_uses_caution_max(req, rules):
    cands = (make_ex("a", {"shoulder": "low"}), make_ex("b"))
    d = evaluate(req(candidates=cands, conditions=(Condition("shoulder", "pain", "self_reported_symptom"),)), rules)
    assert d.allowed_codes == ("b",) and d.pathway == "A"
    rs = dataclasses.replace(rules, caution_max_loading="low")
    assert evaluate(req(candidates=cands, conditions=(Condition("shoulder", "pain", "self_reported_symptom"),)), rs).allowed_codes == ("a", "b")


def test_contraindication(req, rules):
    cands = (make_ex("a", contraindications=(("x", "knee"),)), make_ex("b"))
    d = evaluate(req(candidates=cands, conditions=(Condition("knee", "limited_motion", "self_reported_symptom"),)), rules)
    assert "a" not in d.allowed_codes
    assert evaluate(req(candidates=cands), rules).allowed_codes == ("a", "b")


def test_caution_flag_gives_modification(req, rules):
    cands = (make_ex("a", cautions=(("c", "knee"),)),)
    d = evaluate(req(candidates=cands, conditions=(Condition("knee", "limited_motion", "no_known_limitation"),)), rules)
    assert d.status == S.ALLOW  # no_known_limitation does not count as a limit
    d = evaluate(req(candidates=cands, conditions=(Condition("knee", "limited_motion", "self_reported_symptom"),)), dataclasses.replace(rules, caution_max_loading="high"))
    assert d.status == S.ALLOW_WITH_MODIFICATION and d.per_item[0].caution


def test_incomplete_tags_or_draft_exercise_blocked(req, rules):
    bad = dataclasses.replace(make_ex("bad"), safety_tags_complete=False)
    draft = dataclasses.replace(make_ex("draft"), review_status="draft")
    partial = dataclasses.replace(make_ex("p"), region_loads=make_ex("p").region_loads[:3])
    d = evaluate(req(candidates=(bad, draft, partial, make_ex("ok"))), rules)
    assert d.allowed_codes == ("ok",) and d.status == S.ALLOW_WITH_MODIFICATION


def test_no_candidates_is_allow_with_empty(req, rules):
    d = evaluate(req(candidates=()), rules)
    assert d.status == S.ALLOW and d.allowed_codes == ()


# ---- Path B
def _pain(**kw):
    return Condition("knee", "pain", "self_reported_symptom", "self_reported", active_pain=True, **kw)


def test_path_b_default_conservative(req, rules):
    d = evaluate(req(conditions=(_pain(),)), rules)
    assert d.status == S.STOP_AND_REFER and d.pathway == "B" and "NO_PROGRAM_PATH_B" in d.flags and not d.allowed_codes


def test_path_b_worsening_stops(req, rules):
    d = evaluate(req(conditions=(_pain(worsening=True),)), rules)
    assert E.R_WORSENING in d.reasons and d.status == S.STOP_AND_REFER


def test_path_b_with_published_rules_blocks_related(req, rules):
    rs = dataclasses.replace(rules, path_b_activity_rules_published=True, path_b_related_regions=(("knee", ("hip", "ankle")),))
    cands = (make_ex("a", {"hip": "low"}), make_ex("b", {"shoulder": "low"}))
    d = evaluate(req(candidates=cands, conditions=(_pain(),)), rs)
    assert d.allowed_codes == ("b",) and "PROGRESSION_LOCKED" in d.flags and d.pathway == "B"


def test_path_b_unmapped_region_refers(req, rules):
    rs = dataclasses.replace(rules, path_b_activity_rules_published=True, path_b_related_regions=(("hip", ()),))
    assert evaluate(req(conditions=(_pain(),)), rs).status == S.STOP_AND_REFER


def test_path_b_not_used_when_professional_restriction(req, rules):
    d = evaluate(req(conditions=(_pain(), Condition("knee", "diagnosed_injury", "active_professional_restriction", "professional")),
                     restrictions=(Restriction(region="knee", max_loading="none"),)), rules)
    assert d.pathway == "A"


def test_path_c_requested_refers(req, rules):
    d = evaluate(req(context={"pathway_c_requested": True}), rules)
    assert d.status == S.STOP_AND_REFER and E.R_PATH_C in d.reasons


# ---- clinical rules (data-driven)
def _rule(**kw):
    d = dict(code="SAF-R900", name="t", stage=3, condition={">": [{"var": "age"}, 60]},
             action={"status": "STOP_AND_REFER", "urgency": "non_urgent"}, review_status="published")
    d.update(kw)
    return ClinicalRule(**d)


def test_clinical_rule_published_applies(req, rules):
    rs = dataclasses.replace(rules, clinical_rules=(_rule(),))
    assert evaluate(req(age_years=61), rs).status == S.STOP_AND_REFER
    assert evaluate(req(age_years=60), rs).status == S.ALLOW


def test_clinical_rule_draft_ignored_in_prod(req):
    rs = RuleSet(version=1, status="p", screening_questions=QUESTIONS, clinical_content_published=True,
                 clinical_rules=(_rule(review_status="draft_unreviewed"),))
    assert evaluate(req(age_years=61), rs).status == S.ALLOW


def test_bad_rule_action_failsafe(req, rules):
    rs = dataclasses.replace(rules, clinical_rules=(_rule(action={"status": "ALLOW"}),))
    assert evaluate(req(age_years=61), rs).status == S.ERROR_FAILSAFE


def test_unknown_jsonlogic_op_failsafe(req, rules):
    rs = dataclasses.replace(rules, clinical_rules=(_rule(condition={"eval": 1}),))
    assert evaluate(req(), rs).status == S.ERROR_FAILSAFE


# ---- fail-safe / determinism / integrity
def test_internal_exception_failsafe(req, rules, monkeypatch):
    monkeypatch.setattr(E, "_evaluate", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    d = evaluate(req(), rules)
    assert d.status == S.ERROR_FAILSAFE and E.R_FAILSAFE in d.reasons and d.decision_id and not d.allowed_codes


def test_garbage_input_failsafe(rules):
    assert evaluate(None, rules).status == S.ERROR_FAILSAFE


def test_invalid_enum_and_duplicates_failsafe(req, rules):
    assert evaluate(req(conditions=(Condition("bogus", "pain", "self_reported_symptom"),)), rules).status == S.ERROR_FAILSAFE
    assert evaluate(req(candidates=(make_ex("a"), make_ex("a"))), rules).status == S.ERROR_FAILSAFE
    assert evaluate(req(restrictions=(Restriction(),)), rules).status == S.ERROR_FAILSAFE


def test_deterministic_and_input_sensitive(req, rules):
    a, b = evaluate(req(), rules), evaluate(req(), rules)
    assert a == b and a.decision_id == b.decision_id
    assert evaluate(req(age_years=31), rules).inputs_hash != a.inputs_hash
    assert evaluate(req(), dataclasses.replace(rules, version=2)).inputs_hash != a.inputs_hash


def test_candidate_order_independent(req, rules):
    c = (make_ex("b"), make_ex("a"))
    assert evaluate(req(candidates=c), rules).allowed_codes == evaluate(req(candidates=c[::-1]), rules).allowed_codes == ("a", "b")


def test_fail_closed_never_allows_after_non_permitting_status(req, rules):
    for kw in (dict(age_years=10), dict(consent_health_valid=False), dict(red_flag_answers={"chest_pain": True, "fainting": False})):
        assert not evaluate(req(**kw), rules).allowed_codes


# ---- validate_plan / alternatives / port
def test_validate_plan(req, rules):
    r = req(restrictions=(Restriction(exercise_code="curl"),))
    d = evaluate(r, rules)
    assert validate_plan(["squat"], d, r, rules) == (True, ())
    ok, v = validate_plan(["squat", "curl"], d, r, rules)
    assert not ok and "not-allowed:curl" in v


def test_validate_plan_stale_and_blocked(req, rules):
    r = req()
    d = evaluate(r, rules)
    ok, v = validate_plan(["squat"], d, req(age_years=40), rules)
    assert not ok and "stale-decision:inputs-changed" in v
    r2 = req(consent_health_valid=False)
    ok, v = validate_plan(["squat"], evaluate(r2, rules), r2, rules)
    assert not ok


def test_find_alternatives(req, rules):
    catalog = {c.code: c for c in (make_ex("a"), make_ex("b", {"knee": "high"}), make_ex("c"), make_ex("x"))}
    rel = {"x": [("b", "alternative"), ("a", "alternative"), ("c", "regression"), ("x", "alternative"), ("zz", "alternative")]}
    r = req(restrictions=(Restriction(region="knee", max_loading="none"),))
    assert find_alternatives("x", rel, catalog, r, rules) == ("a", "c")
    assert find_alternatives("a", rel, catalog, r, rules) == ()


def test_safetycore_port(req, rules):
    sc = SafetyCore(rules)
    r = req()
    d = sc.evaluate(r)
    assert sc.validate_plan(["squat"], d, r)[0]
    assert sc.find_alternatives("squat", {}, {}, r) == ()

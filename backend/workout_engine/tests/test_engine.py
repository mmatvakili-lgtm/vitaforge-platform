import dataclasses
import pytest
from safety_core import SafetyCore
from safety_core.models import Condition, Restriction, RuleSet, SafetyRequest
from safety_core.tests.conftest import QUESTIONS, make_ex
from workout_engine import (CatalogExercise, EngineConfig, EngineInput, generate_plan, propose_progression, should_deload)

PATTERNS = [("squat", "main", "quads", {"knee": "high"}), ("hinge", "main", "glutes", {"lower_back": "high"}),
            ("push_horizontal", "main", "chest", {"shoulder": "high"}), ("pull_horizontal", "main", "back", {"shoulder": "low"}),
            ("push_vertical", "accessory", "delts", {"shoulder": "high"}), ("pull_vertical", "accessory", "back", {"shoulder": "low"}),
            ("lunge", "accessory", "quads", {"knee": "high"}), ("core", "accessory", "abs", {})]


def catalog(extra=()):
    out = []
    for p, role, m, loads in PATTERNS:
        for suffix in ("a", "b"):
            out.append(CatalogExercise(make_ex(f"{p}_{suffix}", loads, pattern=p), role, m, "push" if p.startswith("push") else "pull" if p.startswith("pull") else None))
    return tuple(out) + tuple(extra)


@pytest.fixture
def gate():
    return SafetyCore(RuleSet(version=1, status="test", screening_questions=QUESTIONS, allow_unreviewed_content=True))


@pytest.fixture
def base():
    return SafetyRequest(user_id="u", age_years=30, consent_health_valid=True, red_flag_answers={q: False for q in QUESTIONS})


@pytest.fixture
def inp():
    return EngineInput(user_id="u", goal="muscle_gain", level="beginner", days_per_week=3, session_minutes=60,
                       equipment=(), catalog=catalog())


def test_ok_plan_and_label(inp, base, gate):
    r = generate_plan(inp, base, gate)
    assert r.status == "OK" and len(r.days) == 3 and r.label == "experimental" and r.safety_decision_id
    assert r.structure == "full_body" and r.confidence in ("high", "medium")


def test_deterministic(inp, base, gate):
    assert generate_plan(inp, base, gate) == generate_plan(inp, base, gate)


def test_every_exercise_allowed_by_safety(inp, base, gate):
    r = generate_plan(inp, base, gate)
    d = gate.evaluate(dataclasses.replace(base, candidates=tuple(c.candidate for c in inp.catalog)))
    assert set(r.codes) <= set(d.allowed_codes)


def test_restriction_respected(inp, base, gate):
    b = dataclasses.replace(base, restrictions=(Restriction(region="knee", max_loading="none"),))
    r = generate_plan(inp, b, gate)
    assert r.status == "OK" and not any(c.startswith(("squat", "lunge")) for c in r.codes)
    assert any(o.reason == "no-allowed-exercise" for o in r.omissions) and r.confidence == "low"


@pytest.mark.parametrize("kw", [dict(age_years=17), dict(consent_health_valid=False),
                                dict(red_flag_answers={"chest_pain": True, "fainting": False})])
def test_blocked_by_safety_no_plan(inp, base, gate, kw):
    r = generate_plan(inp, dataclasses.replace(base, **kw), gate)
    assert r.status == "BLOCKED" and not r.days and r.safety_decision_id


def test_production_rules_unreviewed_failsafe(inp, base):
    g = SafetyCore(RuleSet(version=1, status="prod", screening_questions=QUESTIONS))
    r = generate_plan(inp, base, g)
    assert r.status == "BLOCKED" and "SAF-R013" in r.reasons


@pytest.mark.parametrize("kw", [dict(goal="x"), dict(level="x"), dict(days_per_week=0), dict(days_per_week=7),
                                dict(session_minutes=10), dict(preferred_structure="zzz")])
def test_needs_info(inp, base, gate, kw):
    assert generate_plan(dataclasses.replace(inp, **kw), base, gate).status == "NEEDS_INFO"


def test_time_budget_drops_accessories(inp, base, gate):
    r = generate_plan(dataclasses.replace(inp, session_minutes=30), base, gate)
    assert all(d.estimated_minutes <= 30 for d in r.days) or r.status == "NEEDS_CONTENT"
    if r.status == "OK":
        assert any(o.reason == "session-time" for o in r.omissions)


def test_too_short_needs_content(inp, base, gate):
    r = generate_plan(dataclasses.replace(inp, session_minutes=20), base, gate)
    assert r.status in ("NEEDS_CONTENT", "OK") and (r.status != "OK" or all(d.estimated_minutes <= 20 for d in r.days))


def test_no_content_needs_content(inp, base, gate):
    r = generate_plan(dataclasses.replace(inp, catalog=()), base, gate)
    assert r.status == "NEEDS_CONTENT"


def test_equipment_and_level_filter(base, gate):
    ex = CatalogExercise(dataclasses.replace(make_ex("bar_squat", {"knee": "high"}, pattern="squat"), equipment=("barbell",),
                                              difficulty="advanced"), "main", "quads")
    inp = EngineInput("u", "strength", "beginner", 3, 60, (), catalog((ex,)))
    assert "bar_squat" not in generate_plan(inp, base, gate).codes
    inp2 = dataclasses.replace(inp, level="advanced", equipment=("barbell",), session_minutes=120)
    assert generate_plan(inp2, base, gate).status == "OK"


def test_structure_selection(inp, base, gate):
    assert generate_plan(dataclasses.replace(inp, days_per_week=4), base, gate).structure == "upper_lower"
    r = generate_plan(dataclasses.replace(inp, days_per_week=3, preferred_structure="ppl"), base, gate)
    assert r.structure == "ppl"
    r = generate_plan(dataclasses.replace(inp, days_per_week=1, preferred_structure="ppl"), base, gate)
    assert r.structure == "full_body" and "preferred-structure-incompatible" in r.reasons


def test_repeat_cap_and_volume(inp, base, gate):
    r = generate_plan(dataclasses.replace(inp, days_per_week=6), base, gate)
    from collections import Counter
    assert max(Counter(r.codes).values()) <= EngineConfig().max_repeat_per_week


def test_gate_failure_on_validate_is_failsafe(inp, base, gate, monkeypatch):
    monkeypatch.setattr(gate, "validate_plan", lambda *a, **k: (False, ("x",)))
    r = generate_plan(inp, base, gate)
    assert r.status == "ERROR_FAILSAFE" and not r.days


def test_internal_error_failsafe(inp, base, gate, monkeypatch):
    monkeypatch.setattr(gate, "evaluate", lambda *_: 1 / 0)
    assert generate_plan(inp, base, gate).status == "ERROR_FAILSAFE"


def test_path_b_no_plan(inp, base, gate):
    b = dataclasses.replace(base, conditions=(Condition("knee", "pain", "self_reported_symptom", "self_reported", active_pain=True),))
    r = generate_plan(inp, b, gate)
    assert r.status == "BLOCKED" and "NO_PROGRAM_PATH_B" in r.flags


# ---- progression
CFG = EngineConfig()


def test_progression_double():
    s = [(10, 3, 20.0, 7.0), (12, 3, 20.0, 7.0)]
    r = propose_progression((), s, 12, 7.0, "barbell", CFG)
    assert r == {"action": "increase_load", "new_load_kg": 22.5, "reps_reset_to_min": True}


@pytest.mark.parametrize("flags,sessions,pain,two", [
    (("PROGRESSION_LOCKED",), [(12, 3, 20, 7), (12, 3, 20, 7)], False, False),
    ((), [(12, 3, 20, 7)], False, False),
    ((), [(12, 3, 20, 7), (12, 3, 20, 7)], True, False),
    ((), [(12, 3, 20, 7), (12, 3, 20, 7)], False, True),
    ((), [(12, 3, 20, 7), (10, 3, 20, 7)], False, False),
    ((), [(12, 3, 20, 7), (12, 3, 20, 9)], False, False)])
def test_progression_blocked(flags, sessions, pain, two):
    assert propose_progression(flags, sessions, 12, 7.0, "barbell", CFG, pain, two) is None


def test_progression_unknown_equipment_default_step():
    s = [(12, 3, 10.0, 6), (12, 3, 10.0, 6)]
    assert propose_progression((), s, 12, 7.0, "weird", CFG)["new_load_kg"] == 11.0


def test_deload():
    assert should_deload(6, [], 7, CFG) and not should_deload(2, [8], 7, CFG)
    assert should_deload(2, [9, 9], 7, CFG) and not should_deload(2, [9, 7], 7, CFG)


def _cat_with_support():
    cat = list(catalog())
    cat = [dataclasses.replace(c, supports_regions=("lower_back",)) if c.code == "core_b" else c for c in cat]
    return tuple(cat)


def test_supportive_preferred_only_when_enabled_and_for_history_without_pain(base, gate):
    inp = EngineInput("u", "general_fitness", "beginner", 3, 90, (), _cat_with_support(), supportive_regions=("lower_back",), supportive_enabled=True)
    assert "core_b" in generate_plan(inp, base, gate).codes
    r = generate_plan(inp, base, gate)
    assert any("supportive" in e.reason for d in r.days for e in d.exercises)
    off = dataclasses.replace(inp, supportive_enabled=False)
    assert not any("supportive" in e.reason for d in generate_plan(off, base, gate).days for e in d.exercises)


def test_supportive_never_overrides_safety(base, gate):
    b = dataclasses.replace(base, restrictions=(Restriction(exercise_code="core_b"),))
    inp = EngineInput("u", "general_fitness", "beginner", 3, 90, (), _cat_with_support(), supportive_regions=("lower_back",), supportive_enabled=True)
    assert "core_b" not in generate_plan(inp, b, gate).codes


def test_main_lifts_first_and_balance_reported(inp, base, gate):
    r = generate_plan(inp, base, gate)
    for d in r.days:
        roles = [next(c for c in inp.catalog if c.code == e.code).role for e in d.exercises]
        assert roles == sorted(roles, key=lambda x: x != "main")
    assert r.balance["push_sets"] > 0 and r.balance["pull_sets"] > 0 and r.balance["weekly_sets_per_muscle"]


def test_recovery_red_reduces_sets_and_recent_codes_rotate(inp, base, gate):
    normal = generate_plan(inp, base, gate)
    red = generate_plan(dataclasses.replace(inp, recovery_state="red"), base, gate)
    assert max(e.sets for d in red.days for e in d.exercises) < max(e.sets for d in normal.days for e in d.exercises)
    assert "recovery:red->sets-1" in red.reasons
    one_day = tuple(e.code for e in normal.days[0].exercises)
    rot = generate_plan(dataclasses.replace(inp, recent_codes=one_day, days_per_week=1), base, gate)
    assert not set(rot.codes) & set(one_day)          # first day's exercises avoided when alternatives exist


def test_equipment_rejection_is_explained_by_safety(inp, base, gate):
    ex = CatalogExercise(dataclasses.replace(make_ex("bb", {"knee": "high"}, pattern="squat"), equipment=("barbell",)), "main", "quads")
    r = generate_plan(dataclasses.replace(inp, catalog=catalog((ex,))), base, gate)
    assert "bb" not in r.codes

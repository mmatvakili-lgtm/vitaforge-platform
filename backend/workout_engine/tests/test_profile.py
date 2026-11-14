import dataclasses
from safety_core import SafetyCore
from safety_core.models import RuleSet, SafetyRequest
from safety_core.tests.conftest import QUESTIONS, make_ex
from workout_engine import CatalogExercise, EngineInput, generate_plan
from workout_engine.tests.test_engine import catalog

GATE = SafetyCore(RuleSet(version=1, status="test", screening_questions=QUESTIONS, allow_unreviewed_content=True))
BASE = SafetyRequest(user_id="u", age_years=30, consent_health_valid=True, red_flag_answers={q: False for q in QUESTIONS})


def ex(code, pattern, role, muscle, difficulty):
    return CatalogExercise(make_ex(code, {}, pattern=pattern, difficulty=difficulty), role, muscle, None)


def inp(extra=(), profile=None, level="advanced", days=3):
    return EngineInput(user_id="u", goal="muscle_gain", level=level, days_per_week=days, session_minutes=60, equipment=(),
                       catalog=catalog(extra), profile=profile)


def profile(levels=None, priorities=None, limiters=(), flags=()):
    lv = {d: {"level": l} for d, l in (levels or {}).items()}
    return {"method": "heuristic_v1", "domains": lv, "priorities": priorities or {}, "limiters": list(limiters), "flags": list(flags)}


def codes(r):
    return [e.code for d in r.days for e in d.exercises]


def test_no_profile_is_unchanged():
    a = generate_plan(inp(), BASE, GATE)
    b = generate_plan(inp(profile={"method": "other"}), BASE, GATE)
    assert a == b and "profile:heuristic_v1" not in a.reasons


def test_difficulty_follows_tested_level():
    extra = (ex("squat_easy", "squat", "main", "quads", "beginner"), ex("squat_hard", "squat", "main", "quads", "advanced"))
    low = generate_plan(inp(extra, profile(levels={"legs": "beginner"})), BASE, GATE)
    high = generate_plan(inp(extra, profile(levels={"legs": "advanced"})), BASE, GATE)
    assert "squat_easy" in codes(low) and "squat_hard" not in codes(low)
    assert "squat_hard" in codes(high)
    assert "profile:heuristic_v1" in low.reasons


def test_weak_pattern_gets_extra_set_within_cap():
    base = generate_plan(inp(profile=profile(levels={"push": "beginner"})), BASE, GATE)
    bumped = generate_plan(inp(profile=profile(levels={"push": "beginner"}, priorities={"push_horizontal": 1.3})), BASE, GATE)
    s0 = {e.code: e.sets for d in base.days for e in d.exercises}
    s1 = {e.code: e.sets for d in bumped.days for e in d.exercises}
    assert any(s1[c] == s0[c] + 1 for c in s1 if c.startswith("push_horizontal"))
    assert any("extra-set:weak-area" in e.reason for d in bumped.days for e in d.exercises)


def test_corrective_added_only_when_allowed():
    cor = (ex("ankle_dorsiflexion_rock", "other", "accessory", "calves", "beginner"),)
    r = generate_plan(inp(cor, profile(limiters=["ankle_mobility"])), BASE, GATE)
    assert all(d.exercises[0].code == "ankle_dorsiflexion_rock" for d in r.days)
    assert "corrective:ankle_mobility:ankle_dorsiflexion_rock" in r.reasons
    absent = generate_plan(inp(profile=profile(limiters=["ankle_mobility"])), BASE, GATE)
    assert "ankle_dorsiflexion_rock" not in codes(absent)


def test_unilateral_preferred_on_asymmetry():
    extra = (ex("split_squat_x", "lunge", "accessory", "quads", "beginner"),)
    r = generate_plan(inp(extra, profile(flags=[{"key": "balance_asymmetry"}]), days=4), BASE, GATE)
    assert "split_squat_x" in codes(r)


def test_profile_never_bypasses_safety():
    r = generate_plan(dataclasses.replace(inp(profile=profile(levels={"legs": "advanced"})), catalog=catalog()), BASE, GATE)
    d = GATE.evaluate(dataclasses.replace(BASE, candidates=tuple(c.candidate for c in catalog())))
    assert set(codes(r)) <= set(d.allowed_codes)

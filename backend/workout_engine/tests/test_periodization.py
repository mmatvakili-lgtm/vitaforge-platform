import pytest

from safety_core import SafetyCore
from safety_core.models import RuleSet, SafetyRequest
from safety_core.tests.conftest import QUESTIONS
from workout_engine import EngineInput, generate_plan
from workout_engine.models import EngineConfig
from workout_engine.periodization import adjust, decide_phase
from workout_engine.tests.test_engine import catalog

GATE = SafetyCore(RuleSet(version=1, status="test", screening_questions=QUESTIONS, allow_unreviewed_content=True))
BASE = SafetyRequest(user_id="u", age_years=30, consent_health_valid=True, red_flag_answers={q: False for q in QUESTIONS})


def plan(**kw):
    return generate_plan(EngineInput(user_id="u", goal="muscle_gain", level="intermediate", days_per_week=3, session_minutes=60, equipment=(),
                                     catalog=catalog(), **kw), BASE, GATE)


def sets_rpe(r):
    ex = [e for d in r.days for e in d.exercises if e.slot != "corrective"]
    return sum(e.sets for e in ex), max(e.rpe for e in ex)


def test_without_block_info_nothing_changes():
    assert plan() == plan(block_week=None, load_signals=())
    assert not any(x.startswith("phase:") for x in plan().reasons)


def test_wave_never_exceeds_standard_and_last_week_deloads():
    std_sets, std_rpe = sets_rpe(plan())
    out = {w: sets_rpe(plan(block_week=w)) for w in (1, 2, 3, 4)}
    for w, (s, r) in out.items():
        assert s <= std_sets and r <= std_rpe, w
    assert out[1][1] < out[2][1] < out[3][1] == std_rpe          # intensity wave rises to the standard target, no higher
    assert out[4][0] < std_sets and out[4][1] <= std_rpe - 2      # deload: fewer sets, much lower RPE


def test_reasons_expose_the_phase():
    assert {"phase:deload", "deload:scheduled:4/4"} <= set(plan(block_week=4).reasons)
    assert {"phase:base", "block-week:1/4"} <= set(plan(block_week=1).reasons)


def test_high_rpe_triggers_automatic_deload_regardless_of_week():
    r = plan(block_week=2, load_signals=("rpe_high",))
    assert "deload:auto:rpe_high" in r.reasons and sets_rpe(r)[0] < sets_rpe(plan())[0]


def test_long_break_eases_in_and_unknown_signals_are_ignored():
    r = plan(block_week=3, load_signals=("inactive",))
    assert "reentry:inactive" in r.reasons and sets_rpe(r)[0] < sets_rpe(plan())[0]
    assert plan(load_signals=("whatever",)) == plan()


def test_deload_is_deterministic_and_safety_still_gates():
    assert plan(block_week=4) == plan(block_week=4)
    assert plan(block_week=4).status == "OK"


@pytest.mark.parametrize("phase", ["standard", "base", "build", "peak", "deload", "reentry"])
@pytest.mark.parametrize("sets,rpe", [(2, 4.0), (3, 7.0), (5, 9.5)])
def test_adjust_is_monotone_non_increasing(phase, sets, rpe):
    s2, r2 = adjust(phase, sets, rpe, 0.6)
    assert 1 <= s2 <= sets and r2 <= rpe and r2 >= min(5.0, rpe) - 1e-9


def test_decide_phase_edges():
    assert decide_phase(None)[0] == "standard"
    assert decide_phase(9, (), 4)[0] == "deload"          # clamped to the block length
    assert decide_phase(1, (), 1)[0] == "standard"        # degenerate block length disables the wave
    assert decide_phase(2, ("rpe_high", "inactive"))[0] == "deload"   # fatigue wins over re-entry

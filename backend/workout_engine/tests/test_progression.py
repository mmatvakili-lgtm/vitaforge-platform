import pytest
from workout_engine import EngineConfig
from workout_engine.progression import (ProgressionConfig, RecoveryInput, SessionPerf, SetLog, assess_recovery, decide)

C = EngineConfig()


def sess(day, reps, load=20.0, rpe=7.0, n=3, **kw):
    return SessionPerf(day, tuple(SetLog(reps, load, rpe) for _ in range(n)), kw.pop("planned_sets", 3), kw.pop("rep_min", 8), kw.pop("rep_max", 12), **kw)


def test_increase_load_at_top_of_range():
    d = decide([sess(1, 11), sess(3, 12)], (), "barbell", C)
    assert d.action == "increase_load" and d.params["new_load_kg"] == 22.5 and d.reasons == ("top-of-range-and-rpe-ok",)


def test_increase_reps_inside_range():
    d = decide([sess(1, 9), sess(3, 10)], (), "dumbbell", C)
    assert d.action == "increase_reps" and d.params["target_reps"] == 11


def test_not_easy_holds():
    assert decide([sess(1, 12, rpe=9), sess(3, 12, rpe=9)], (), "barbell", C).action == "hold"


@pytest.mark.parametrize("flags,hist,action", [
    (("PROGRESSION_LOCKED",), [sess(1, 12), sess(3, 12)], "locked"),
    ((), [sess(1, 12), sess(3, 12, pain_reported=True)], "pause_pain"),
    ((), [sess(1, 12)], "insufficient_data"),
    ((), [], "insufficient_data"),
])
def test_blocking_states(flags, hist, action):
    assert decide(hist, flags, "barbell", C).action == action


def test_repeated_pain_flags_reassessment():
    d = decide([sess(1, 10, pain_reported=True), sess(3, 10, pain_reported=True)], (), "barbell", C)
    assert d.action == "pause_pain" and "REASSESSMENT_RECOMMENDED" in d.flags


def test_low_adherence_holds():
    h = [sess(1, 12, n=1), sess(3, 12, n=1), sess(5, 12, n=3)]
    d = decide(h, (), "barbell", C)
    assert d.action == "hold" and d.reasons == ("low-adherence",)
    assert decide([sess(1, 12), sess(2, 12), SessionPerf(3, (), 3, 8, 12, completed=False), SessionPerf(4, (), 3, 8, 12, completed=False), sess(5, 12)], (), "barbell", C).reasons == ("low-adherence",)


def test_high_fatigue_suggests_deload_not_forced():
    d = decide([sess(1, 12, fatigue=9), sess(3, 12, fatigue=8)], (), "barbell", C)
    assert d.action == "suggest_deload" and d.params["factor"] == C.deload_factor


def test_below_floor_twice_reduces_load():
    d = decide([sess(1, 6), sess(3, 7)], (), "barbell", C)
    assert d.action == "reduce_load" and d.params["new_load_kg"] == 18.0


def test_stall_detected_with_flag():
    h = [sess(1, 9), sess(3, 9), sess(5, 9), sess(7, 8)]
    d = decide(h, (), "barbell", C)
    assert d.action == "suggest_deload" and "STALLED" in d.flags and d.reasons == ("stalled-no-improvement",)


def test_improving_not_stalled():
    h = [sess(1, 8), sess(3, 9), sess(5, 10), sess(7, 11)]
    assert decide(h, (), "barbell", C).action in ("increase_reps", "hold")


def test_one_variable_at_a_time():
    d = decide([sess(1, 12), sess(3, 12)], (), "barbell", C, weekly_volume_change_pending=True)
    assert d.action == "hold" and d.reasons == ("one-variable-at-a-time",)


def test_decisions_are_deterministic_and_explainable():
    h = [sess(1, 11), sess(3, 12)]
    assert decide(h, (), "barbell", C) == decide(list(reversed(h)), (), "barbell", C)
    d = decide(h, (), "barbell", C)
    assert d.reasons and d.evidence


@pytest.mark.parametrize("inp,state", [
    (RecoveryInput(3, 3), "unknown"), (RecoveryInput(3, 3, 3, 3, 7.5), "green"), (RecoveryInput(3, 3, 6.5, 3, 7), "amber"),
    (RecoveryInput(3, 3, 8.5, 3, 7), "red"), (RecoveryInput(3, 3, 3, 3, 7, pain_reports_last7=2), "red"),
    (RecoveryInput(3, 3, 3, 3, 4), "amber"), (RecoveryInput(5, 3, 3, 3, 7), "amber"), (RecoveryInput(0, 0, pain_reports_last7=1), "amber")])
def test_recovery_states(inp, state):
    assert assess_recovery(inp).state == state


def test_recovery_never_claims_low_uncertainty():
    assert assess_recovery(RecoveryInput(3, 3, 3, 3, 7.5)).uncertainty == "medium" and assess_recovery(RecoveryInput(3, 3, 3)).uncertainty == "high"

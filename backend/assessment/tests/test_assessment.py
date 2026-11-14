import pytest

from assessment import AssessmentError, evaluate


def full(**kw):
    base = dict(squat_reps=25, squat_heels_down=True, squat_knees_cave=False, hinge_reach="toes", glute_bridge_s=45, push_variant="standard",
                push_reps=15, pull_variant="inverted_row", pull_reps=8, plank_s=60, side_plank_left_s=30, side_plank_right_s=30,
                balance_left_s=30, balance_right_s=30, overhead_reach="yes", ankle_knee_to_wall_cm=10, cardio_minutes=20)
    base.update(kw)
    return base


def test_deterministic_and_labelled():
    a, b = evaluate(full()), evaluate(full())
    assert a == b and a["method"] == "heuristic_v1" and a["content_status"] == "ai_curated"
    assert all(0 <= d["score"] <= 100 for d in a["domains"].values())


def test_monotone_more_reps_never_lowers_score():
    prev = -1
    for r in range(0, 31):
        s = evaluate(full(push_reps=r))["domains"]["push"]["score"]
        assert s >= prev
        prev = s


def test_variant_ordering_and_bands():
    s = lambda v: evaluate(full(push_variant=v, push_reps=20))["domains"]["push"]["score"]
    assert s("wall") < s("knee") < s("standard")
    assert evaluate(full(push_variant="wall", push_reps=0))["domains"]["push"]["band"] == "foundation"


def test_weakness_and_priority_follow_the_data():
    p = evaluate(full(pull_variant="inverted_row", pull_reps=1))
    assert p["weaknesses"][0]["domain"] == "pull"
    assert p["priorities"]["pull_horizontal"] > 1.0
    assert any(f["key"] == "push_pull_imbalance" and f["lagging"] == "pull" for f in p["flags"])


def test_asymmetry_detected_with_weaker_side():
    p = evaluate(full(balance_left_s=10, balance_right_s=30))
    f = [x for x in p["flags"] if x["key"] == "balance_asymmetry"][0]
    assert f["weaker_side"] == "left" and f["gap_pct"] == 67
    assert not [x for x in evaluate(full(balance_left_s=28, balance_right_s=30))["flags"] if x["key"] == "balance_asymmetry"]


def test_limiters_and_overhead_dampens_vertical_press():
    p = evaluate(full(overhead_reach="no", ankle_knee_to_wall_cm=4, squat_heels_down=False, squat_knees_cave=True, hinge_reach="shin"))
    assert {"overhead_mobility", "ankle_mobility", "squat_heel_lift", "knee_control", "posterior_chain_mobility"} <= set(p["limiters"])
    assert p["priorities"]["push_vertical"] <= 0.8
    assert "corrective_ankle_mobility" in p["corrective_focus"]


def test_untested_domains_are_not_scored_as_zero():
    p = evaluate({"push_variant": "standard", "push_reps": 10, "pull_variant": "none"})
    assert p["domains"]["pull"]["score"] is None and "pull" in p["untested"] and p["tested_count"] == 1


def test_pain_is_flagged_not_interpreted():
    p = evaluate(full(pain_regions=["knee", "knee", "shoulder"]))
    assert p["pain_reported"] and p["pain_regions"] == ["knee", "shoulder"] and p["domains"]["legs"]["caution"]


@pytest.mark.parametrize("bad", [{}, {"pain_regions": ["knee"]}, {"squat_reps": -1}, {"squat_reps": 101}, {"squat_reps": True}, {"squat_reps": 5.5},
                                 {"push_variant": "x"}, {"plank_s": "9"}, {"nope": 1}, {"squat_heels_down": 1}, {"pain_regions": ["moon"]}, "x"])
def test_invalid_input_rejected(bad):
    with pytest.raises(AssessmentError):
        evaluate(bad)

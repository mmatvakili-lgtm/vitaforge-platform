"""Regression gates for the real exercise bank: no dead ends across goal/level/days/equipment/time, and every training day mixes several body regions."""
import itertools

import pytest

from e2e.test_scenarios import build, signup

EQ = {"none": [], "band": ["band"], "dumbbell": ["dumbbell"],
      "gym": ["dumbbell", "bench", "barbell", "machine", "cable", "pull_up_bar", "box", "kettlebell", "band"]}


@pytest.fixture(scope="module")
def h():
    return build()


@pytest.mark.parametrize("days,eq,minutes,level", list(itertools.product([1, 2, 3, 4, 5, 6], EQ, [30, 60], ["beginner", "advanced"])))
def test_every_combination_yields_a_plan(h, days, eq, minutes, level):
    t = signup(h, f"b{days}{eq}{minutes}{level}@ex.com", level=level, goal="strength", days=days, minutes=minutes, equipment=EQ[eq])
    r = h.call("POST", "/workouts/generate", {}, token=t)
    assert r.status == 200, r.body
    plan = r.body["plan"]
    assert len(plan["days"]) == days
    for d in plan["days"]:
        assert len(d["exercises"]) >= 2 and d["est_minutes"] <= minutes


@pytest.mark.parametrize("days", [3, 4, 5, 6])
def test_gym_days_are_multi_muscle_and_week_is_balanced(h, days):
    t = signup(h, f"m{days}@ex.com", level="intermediate", goal="muscle_gain", days=days, minutes=75, equipment=EQ["gym"])
    plan = h.call("POST", "/workouts/generate", {}, token=t).body["plan"]
    week = set()
    for d in plan["days"]:
        muscles = {m for e in d["exercises"] for m in e["muscles"]}
        assert len(muscles) >= 4, (d["title"], muscles)             # never a single-muscle day
        week |= muscles
    assert len(week) >= 9                                           # the week covers most of the body
    reasons = " ".join(plan["rationale"]["reasons"])
    assert "WO-C06" not in reasons

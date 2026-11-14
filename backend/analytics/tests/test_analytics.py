from analytics import build
from analytics.engine import epley

T = 800000
M = {"squat": "quads", "bench": "chest"}


def sess(day_ago, logs):
    return {"finished": True, "start": T - day_ago, "logs": logs}


def L(code, reps, kg, rpe=None, pr=False, skipped=False):
    return {"code": code, "reps": reps, "load_kg": kg, "rpe": rpe, "pr": pr, "skipped": skipped}


def test_epley_and_limits():
    assert epley(100, 5) == 116.7 and epley(0, 5) is None and epley(100, 13) is None and epley(100, 0) is None


def test_empty_is_insufficient_not_error():
    r = build([], T, M)
    assert r["insights"] == [{"key": "insufficient_data", "params": {}}] and r["e1rm"] == [] and r["streak_weeks"] == 0
    assert len(r["weeks"]) == 8


def test_e1rm_trend_and_weekly_volume():
    s = [sess(20, [L("squat", 5, 100)]), sess(1, [L("squat", 5, 110, pr=True), L("squat", 20, 50)])]
    r = build(s, T, M)
    sq = r["e1rm"][0]
    assert sq["code"] == "squat" and sq["latest"] == 128.3 and sq["change_pct"] == 9.9     # 20-rep set ignored for the estimate
    assert sq["series"][-1] == 128.3 and r["records_4w"] == 1
    assert r["weeks"][-1]["sets"] == 2 and r["weeks"][-1]["volume_kg"] == 110 * 5 + 50 * 20
    assert {"key": "e1rm_up", "params": {"code": "squat", "pct": 9.9}} in r["insights"]


def test_skipped_and_unfinished_ignored():
    s = [sess(1, [L("squat", 0, 0, skipped=True)]), {"finished": False, "start": T - 1, "logs": [L("squat", 5, 100)]}]
    r = build(s, T, M)
    assert r["e1rm"] == [] and r["weeks"][-1]["sets"] == 0


def test_muscle_bands_and_streak_and_inactive():
    s = [sess(d, [L("bench", 8, 40)] * 3) for d in (1, 8, 15, 22)]
    r = build(s, T, M)
    m = {x["muscle"]: x for x in r["muscles"]}
    assert m["chest"]["status"] == "low" and r["streak_weeks"] == 4
    assert any(i["key"] == "muscle_low" for i in r["insights"])
    r2 = build([sess(12, [L("bench", 8, 40)])], T, M)
    assert {"key": "inactive", "params": {"days": 12}} in r2["insights"]


def test_volume_drop_and_rpe_high_and_deterministic():
    s = [sess(d, [L("bench", 8, 60, rpe=9.5)] * 3) for d in (22, 15)] + [sess(d, [L("bench", 8, 20, rpe=9.5)] * 3) for d in (8, 1)]
    r = build(s, T, M)
    keys = {i["key"] for i in r["insights"]}
    assert "volume_drop" in keys and "rpe_high" in keys
    assert build(s, T, M) == r


def test_old_sessions_outside_window_ignored():
    assert build([sess(60, [L("squat", 5, 100)])], T, M)["e1rm"] == []

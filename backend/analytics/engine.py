"""Deterministic training analytics from a user's own finished sessions (method ``analytics_v1``).

Everything here is descriptive: estimates are labelled estimates, thresholds are project-authored heuristics (not published norms), and the
output carries message keys + params only, so the UI localises it. Nothing here approves, prescribes or changes a plan.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

METHOD = "analytics_v1"
WEEKS = 8
SETS_LOW, SETS_HIGH = 6, 20           # weekly hard-set band per muscle (heuristic, general-population guidance; not individualised)
E1RM_MAX_REPS = 12                    # Epley is unreliable above ~12 reps -> such sets are ignored for the estimate


def epley(load_kg: float, reps: int) -> Optional[float]:
    if load_kg <= 0 or reps <= 0 or reps > E1RM_MAX_REPS:
        return None
    return round(load_kg * (1 + reps / 30), 1)


def _week_index(day: int, today: int) -> int:
    """0 = the 7 days ending today, 1 = the 7 days before that, ..."""
    return (today - day) // 7


def build(sessions: Iterable[Mapping[str, Any]], today: int, muscle_of: Mapping[str, str], name_of: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    name_of = name_of or {}
    done = [s for s in sessions if s.get("finished") and 0 <= today - s["start"] < WEEKS * 7]
    weeks: List[Dict[str, Any]] = [{"week_ago": i, "sessions": 0, "sets": 0, "volume_kg": 0.0} for i in range(WEEKS)]
    best_by_week: Dict[str, Dict[int, float]] = {}
    muscle_week: Dict[str, List[int]] = {}
    rpes: Dict[int, List[float]] = {}
    pr_count = 0
    for s in done:
        w = _week_index(s["start"], today)
        weeks[w]["sessions"] += 1
        for l in s["logs"]:
            if l.get("skipped") or l.get("reps", 0) <= 0:
                continue
            weeks[w]["sets"] += 1
            weeks[w]["volume_kg"] += l["reps"] * l["load_kg"]
            if w < 4 and l.get("pr"):
                pr_count += 1
            m = muscle_of.get(l["code"])
            if m:
                muscle_week.setdefault(m, [0] * WEEKS)[w] += 1
            e = epley(l["load_kg"], l["reps"])
            if e is not None:
                cur = best_by_week.setdefault(l["code"], {})
                cur[w] = max(cur.get(w, 0.0), e)
            if l.get("rpe") is not None:
                rpes.setdefault(w, []).append(float(l["rpe"]))
    for x in weeks:
        x["volume_kg"] = round(x["volume_kg"], 1)

    e1rm = []
    for code, by_w in best_by_week.items():
        series = [by_w.get(w) for w in range(WEEKS - 1, -1, -1)]       # oldest -> newest, None = no qualifying set that week
        known = [(w, v) for w, v in by_w.items()]
        newest_w = min(w for w, _ in known)
        latest = by_w[newest_w]
        older = [v for w, v in known if w > newest_w and w <= newest_w + 4]
        change = round((latest - max(older)) / max(older) * 100, 1) if older else None
        e1rm.append({"code": code, "name": name_of.get(code), "latest": latest, "best": max(by_w.values()), "change_pct": change, "series": series})
    e1rm.sort(key=lambda r: (-r["best"], r["code"]))

    muscles = []
    for m, counts in sorted(muscle_week.items()):
        recent = counts[0] + counts[1]
        avg4 = round(sum(counts[:4]) / 4, 1)
        status = "low" if avg4 < SETS_LOW else "high" if avg4 > SETS_HIGH else "ok"
        muscles.append({"muscle": m, "sets_last_week": counts[0], "avg_weekly_sets_4w": avg4, "status": status, "recent_two_weeks": recent})

    active_weeks = [i for i, x in enumerate(weeks) if x["sessions"]]
    streak = 0
    for i in range(WEEKS):
        if weeks[i]["sessions"] or (i == 0 and weeks[1]["sessions"]):      # the running week does not break a streak until it ends
            if weeks[i]["sessions"]:
                streak += 1
        else:
            break
    last_day = max((s["start"] for s in done), default=None)
    days_since = today - last_day if last_day is not None else None

    insights: List[Dict[str, Any]] = []
    if not done:
        insights.append({"key": "insufficient_data", "params": {}})
    else:
        prev = [weeks[i]["volume_kg"] for i in range(2, 6) if weeks[i]["sessions"]]      # baseline: weeks 3-6 back vs the last two
        recent_vol = weeks[0]["volume_kg"] + weeks[1]["volume_kg"]
        if prev and len(prev) >= 2:
            base = sum(prev) / len(prev) * 2
            if base > 0 and recent_vol < 0.6 * base:
                insights.append({"key": "volume_drop", "params": {"pct": round((1 - recent_vol / base) * 100)}})
        for r in e1rm[:6]:
            if r["change_pct"] is not None and r["change_pct"] >= 2.5:
                insights.append({"key": "e1rm_up", "params": {"code": r["code"], "pct": r["change_pct"]}})
        for m in muscles:
            if m["status"] == "low" and m["recent_two_weeks"]:
                insights.append({"key": "muscle_low", "params": {"muscle": m["muscle"], "avg": m["avg_weekly_sets_4w"]}})
            elif m["status"] == "high":
                insights.append({"key": "muscle_high", "params": {"muscle": m["muscle"], "avg": m["avg_weekly_sets_4w"]}})
        hi = [v for w in (0, 1) for v in rpes.get(w, [])]
        if len(hi) >= 6 and sum(hi) / len(hi) >= 9:
            insights.append({"key": "rpe_high", "params": {"avg": round(sum(hi) / len(hi), 1)}})
        if days_since is not None and days_since >= 10:
            insights.append({"key": "inactive", "params": {"days": days_since}})
        if pr_count:
            insights.append({"key": "records", "params": {"count": pr_count}})
    return {"method": METHOD, "content_status": "ai_curated", "weeks": list(reversed(weeks)), "e1rm": e1rm[:12], "muscles": muscles,
            "streak_weeks": streak, "days_since_last": days_since, "records_4w": pr_count, "insights": insights[:8],
            "thresholds": {"sets_low": SETS_LOW, "sets_high": SETS_HIGH, "e1rm_max_reps": E1RM_MAX_REPS}}

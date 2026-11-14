"""Deterministic movement self-assessment (method ``heuristic_v1``, content status ``ai_curated``).

All cut-offs below are project-authored heuristics for general fitness screening, NOT published norms and NOT clinically validated.
The engine only describes the user (profile + priorities). It never approves an exercise: the Safety Core remains the sole approver.
Output texts are message keys with params, so the UI localises them and no clinical-sounding prose lives in the backend.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from safety_core.models import REGIONS

METHOD = "heuristic_v1"
DOMAINS = ("legs", "hinge", "push", "pull", "core", "balance", "mobility", "cardio")
STRENGTH_DOMAINS = ("legs", "hinge", "push", "pull", "core")
VARIANT_BANDS = {"push": {"wall": (0, 20), "incline": (20, 40), "knee": (30, 50), "standard": (40, 100)},
                 "pull": {"inverted_row": (15, 45), "band_assisted": (30, 60), "pullup": (50, 100)}}
VARIANT_CAP = {"push": {"wall": 20, "incline": 20, "knee": 20, "standard": 30}, "pull": {"inverted_row": 15, "band_assisted": 10, "pullup": 10}}
HINGE_REACH = {"above_knee": 10, "shin": 35, "toes": 65, "palms_floor": 90}
OVERHEAD = {"no": 0, "partial": 50, "yes": 100}

# field -> (kind, bounds_or_choices)
FIELDS: Dict[str, tuple] = {
    "squat_reps": ("int", (0, 100)), "squat_heels_down": ("bool", None), "squat_knees_cave": ("bool", None),
    "hinge_reach": ("enum", tuple(HINGE_REACH)), "glute_bridge_s": ("int", (0, 180)),
    "push_variant": ("enum", tuple(VARIANT_BANDS["push"])), "push_reps": ("int", (0, 100)),
    "pull_variant": ("enum", ("none",) + tuple(VARIANT_BANDS["pull"])), "pull_reps": ("int", (0, 50)),
    "plank_s": ("int", (0, 300)), "side_plank_left_s": ("int", (0, 180)), "side_plank_right_s": ("int", (0, 180)),
    "balance_left_s": ("int", (0, 60)), "balance_right_s": ("int", (0, 60)),
    "overhead_reach": ("enum", tuple(OVERHEAD)), "ankle_knee_to_wall_cm": ("int", (0, 20)),
    "cardio_minutes": ("int", (0, 60)),
    "pain_regions": ("regions", None),
}


class AssessmentError(ValueError):
    pass


def _clamp(x: float) -> int:
    return int(round(max(0.0, min(100.0, x))))


def _band(score: Optional[int]) -> Optional[str]:
    if score is None:
        return None
    return "foundation" if score < 25 else "developing" if score < 50 else "solid" if score < 75 else "strong"


def _level(score: Optional[int]) -> Optional[str]:
    if score is None:
        return None
    return "beginner" if score < 35 else "intermediate" if score < 70 else "advanced"


def _validate(answers: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(answers, dict):
        raise AssessmentError("answers")
    clean: Dict[str, Any] = {}
    for k, v in answers.items():
        if k not in FIELDS:
            raise AssessmentError(f"unknown:{k}")
        if v is None:
            continue
        kind, spec = FIELDS[k]
        if kind == "int":
            if isinstance(v, bool) or not isinstance(v, int) or not spec[0] <= v <= spec[1]:
                raise AssessmentError(f"range:{k}")
        elif kind == "bool":
            if not isinstance(v, bool):
                raise AssessmentError(f"type:{k}")
        elif kind == "enum":
            if v not in spec:
                raise AssessmentError(f"enum:{k}")
        elif kind == "regions":
            if not isinstance(v, list) or len(v) > len(REGIONS) or any(r not in REGIONS for r in v):
                raise AssessmentError(f"regions:{k}")
            v = sorted(set(v))
        clean[k] = v
    if not any(k != "pain_regions" for k in clean):
        raise AssessmentError("empty")
    return clean


def _variant_score(domain: str, variant: Optional[str], reps: Optional[int]) -> Optional[int]:
    if variant is None or variant == "none":
        return None
    lo, hi = VARIANT_BANDS[domain][variant]
    frac = min((reps or 0) / VARIANT_CAP[domain][variant], 1.0)
    return _clamp(lo + (hi - lo) * frac)


def _scores(a: Dict[str, Any]) -> Dict[str, Optional[int]]:
    s: Dict[str, Optional[int]] = {d: None for d in DOMAINS}
    parts = []
    if "squat_reps" in a:
        q = min(a["squat_reps"] / 30, 1.0) * 70
        q += 15 if a.get("squat_heels_down", True) else 0
        q += 15 if not a.get("squat_knees_cave", False) else 0
        parts.append(q)
    s["legs"] = _clamp(sum(parts)) if parts else None
    h = []
    if "hinge_reach" in a:
        h.append(HINGE_REACH[a["hinge_reach"]])
    if "glute_bridge_s" in a:
        h.append(min(a["glute_bridge_s"] / 60, 1.0) * 100)
    s["hinge"] = _clamp(sum(h) / len(h)) if h else None
    s["push"] = _variant_score("push", a.get("push_variant"), a.get("push_reps")) if "push_variant" in a else None
    s["pull"] = _variant_score("pull", a.get("pull_variant"), a.get("pull_reps")) if "pull_variant" in a else None
    c = []
    if "plank_s" in a:
        c.append(min(a["plank_s"] / 90, 1.0) * 100)
    sides = [a[k] for k in ("side_plank_left_s", "side_plank_right_s") if k in a]
    if sides:
        c.append(min(min(sides) / 45, 1.0) * 100)        # the weaker side limits the score
    s["core"] = _clamp(sum(c) / len(c)) if c else None
    b = [a[k] for k in ("balance_left_s", "balance_right_s") if k in a]
    s["balance"] = _clamp(min(min(b) / 30, 1.0) * 100) if b else None
    m = []
    if "overhead_reach" in a:
        m.append(OVERHEAD[a["overhead_reach"]])
    if "ankle_knee_to_wall_cm" in a:
        m.append(min(a["ankle_knee_to_wall_cm"] / 10, 1.0) * 100)
    if "hinge_reach" in a:
        m.append(HINGE_REACH[a["hinge_reach"]])
    s["mobility"] = _clamp(sum(m) / len(m)) if m else None
    s["cardio"] = _clamp(min(a["cardio_minutes"] / 30, 1.0) * 100) if "cardio_minutes" in a else None
    return s


def _asymmetry(a: Dict[str, Any], left: str, right: str, key: str) -> Optional[Dict[str, Any]]:
    if left not in a or right not in a:
        return None
    lo, hi = sorted((a[left], a[right]))
    if hi == 0 or hi - lo < 5 or (hi - lo) / hi < 0.25:
        return None
    return {"key": key, "weaker_side": "left" if a[left] < a[right] else "right", "gap_pct": round((hi - lo) / hi * 100)}


def evaluate(answers: Dict[str, Any]) -> Dict[str, Any]:
    a = _validate(answers)
    sc = _scores(a)
    tested = {d: v for d, v in sc.items() if v is not None}
    mean = sum(tested.values()) / len(tested) if tested else 0.0
    ranked = sorted(tested.items(), key=lambda kv: kv[1])
    weaknesses = [{"domain": d, "score": v} for d, v in ranked if v <= mean - 10][:3]
    strengths = [{"domain": d, "score": v} for d, v in reversed(ranked) if v >= mean + 10][:3]
    flags: List[Dict[str, Any]] = []
    for k in (_asymmetry(a, "side_plank_left_s", "side_plank_right_s", "side_plank_asymmetry"),
              _asymmetry(a, "balance_left_s", "balance_right_s", "balance_asymmetry")):
        if k:
            flags.append(k)
    if sc["push"] is not None and sc["pull"] is not None and abs(sc["push"] - sc["pull"]) >= 25:
        flags.append({"key": "push_pull_imbalance", "lagging": "pull" if sc["pull"] < sc["push"] else "push", "gap": abs(sc["push"] - sc["pull"])})
    limiters: List[str] = []
    if a.get("overhead_reach") in ("no", "partial"):
        limiters.append("overhead_mobility")
    if "ankle_knee_to_wall_cm" in a and a["ankle_knee_to_wall_cm"] < 9:
        limiters.append("ankle_mobility")
    if a.get("squat_heels_down") is False:
        limiters.append("squat_heel_lift")
    if a.get("squat_knees_cave"):
        limiters.append("knee_control")
    if a.get("hinge_reach") in ("above_knee", "shin"):
        limiters.append("posterior_chain_mobility")
    pain = a.get("pain_regions", [])
    # Priorities feed the planner as relative weights only (1.0 = neutral). Weak domains get more, strong ones less.
    pattern_of = {"legs": ("squat", "lunge"), "hinge": ("hinge",), "push": ("push_horizontal", "push_vertical"),
                  "pull": ("pull_horizontal", "pull_vertical"), "core": ("core", "rotation", "carry")}
    priorities = {p: 1.0 for ps in pattern_of.values() for p in ps}
    for d, ps in pattern_of.items():
        if d in tested:
            w = 1.0 + max(-0.2, min(0.4, (mean - tested[d]) / 100 * 1.6))
            for p in ps:
                priorities[p] = round(w, 2)
    if "overhead_mobility" in limiters:
        priorities["push_vertical"] = round(min(priorities["push_vertical"], 0.8), 2)
    corrective = [f"corrective_{k}" for k in limiters]
    domains = {d: {"score": sc[d], "band": _band(sc[d]), "level": _level(sc[d]), "tested": sc[d] is not None,
                   "caution": bool(pain)} for d in DOMAINS}
    strength_scores = [sc[d] for d in STRENGTH_DOMAINS if sc[d] is not None]
    overall = _level(sum(strength_scores) / len(strength_scores)) if strength_scores else None
    return {"method": METHOD, "content_status": "ai_curated", "answers": a, "domains": domains, "overall_level": overall,
            "tested_count": len(tested), "strengths": strengths, "weaknesses": weaknesses, "flags": flags, "limiters": limiters,
            "priorities": priorities, "corrective_focus": corrective, "pain_reported": bool(pain), "pain_regions": pain,
            "untested": [d for d in DOMAINS if sc[d] is None]}

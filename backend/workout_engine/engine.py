"""Deterministic workout plan generator (DOC-11). No LLM. Every exercise passes Safety Core twice."""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Sequence, Tuple

from safety_core import SafetyCore
from safety_core.models import SafetyRequest

from .models import (GOALS, LEVELS, LEVEL_RANK, STRUCTURES, CatalogExercise, EngineConfig, EngineInput, Omission,
                     PlanResult, PlannedDay, PlannedExercise)

# (goal, level_group) -> sets, reps_min, reps_max, rpe, rest_seconds       (Unverified defaults, DOC-11 §6)
PRESCRIPTION = {
    ("strength", "beginner"): (3, 5, 8, 6.5, 150),
    ("strength", "advanced"): (4, 3, 6, 7.5, 200),
    ("muscle_gain", "beginner"): (3, 8, 12, 6.5, 75),
    ("muscle_gain", "advanced"): (3, 6, 12, 8.0, 90),
    ("general_fitness", "beginner"): (2, 10, 15, 6.0, 60),
    ("general_fitness", "advanced"): (3, 10, 15, 6.0, 60),
    ("fat_loss", "beginner"): (2, 10, 15, 7.0, 60),
    ("fat_loss", "advanced"): (3, 10, 15, 7.0, 60),
}

# slot = (name, movement_pattern, role)
FULL_BODY = [("squat", "squat", "main"), ("hinge", "hinge", "main"), ("push", "push_horizontal", "main"),
             ("pull", "pull_horizontal", "main"), ("core", "core", "accessory")]
UPPER = [("push_h", "push_horizontal", "main"), ("pull_h", "pull_horizontal", "main"), ("push_v", "push_vertical", "accessory"),
         ("pull_v", "pull_vertical", "accessory")]
LOWER = [("squat", "squat", "main"), ("hinge", "hinge", "main"), ("lunge", "lunge", "accessory"), ("core", "core", "accessory")]
PUSH = [("push_h", "push_horizontal", "main"), ("push_v", "push_vertical", "accessory"), ("core", "core", "accessory")]
PULL = [("pull_h", "pull_horizontal", "main"), ("pull_v", "pull_vertical", "accessory"), ("core", "core", "accessory")]
LEGS = LOWER

DAY_TEMPLATES = {
    "full_body": [("Full Body A", FULL_BODY), ("Full Body B", FULL_BODY), ("Full Body C", FULL_BODY)],
    "upper_lower": [("Upper A", UPPER), ("Lower A", LOWER), ("Upper B", UPPER), ("Lower B", LOWER)],
    "ppl": [("Push", PUSH), ("Pull", PULL), ("Legs", LEGS)],
}
DEFAULT_STRUCTURE = {1: "full_body", 2: "full_body", 3: "full_body", 4: "upper_lower", 5: "upper_lower", 6: "ppl"}
COMPATIBLE = {1: {"full_body"}, 2: {"full_body"}, 3: {"full_body", "ppl"}, 4: {"upper_lower", "full_body"},
              5: {"upper_lower", "ppl"}, 6: {"ppl", "upper_lower"}}


def _group(level: str) -> str:
    return "beginner" if level == "beginner" else "advanced"


def _day_names(structure: str, n: int) -> List[Tuple[str, list]]:
    base = DAY_TEMPLATES[structure]
    return [base[i % len(base)] if structure != "ppl" else base[i % 3] for i in range(n)]


def _fail(status, reasons, decision=None, cfg: Optional[EngineConfig] = None, flags=(), omissions=()):
    return PlanResult(status=status, reasons=tuple(reasons), omissions=tuple(omissions), safety_decision_id=getattr(decision, "decision_id", None),
                      rule_set_version=getattr(decision, "rule_set_version", None),
                      config_version=getattr(cfg, "version", None), flags=tuple(flags))


def generate_plan(inp: EngineInput, base_request: SafetyRequest, gate: SafetyCore) -> PlanResult:
    """S0..S8 of DOC-11 §3. Never raises; internal error -> ERROR_FAILSAFE (no plan)."""
    try:
        return _generate(inp, base_request, gate)
    except Exception as exc:  # noqa: BLE001
        return _fail("ERROR_FAILSAFE", ("WO-ERR", type(exc).__name__), cfg=getattr(inp, "config", None))


def _generate(inp: EngineInput, base: SafetyRequest, gate: SafetyCore) -> PlanResult:
    cfg = inp.config
    # S0 validate
    missing = []
    if inp.goal not in GOALS: missing.append("goal")
    if inp.level not in LEVELS: missing.append("level")
    if not 1 <= inp.days_per_week <= 6: missing.append("days_per_week")
    if inp.session_minutes < 20: missing.append("session_minutes")
    if inp.preferred_structure is not None and inp.preferred_structure not in STRUCTURES: missing.append("preferred_structure")
    if missing:
        return _fail("NEEDS_INFO", ["WO-NEEDS-INFO:" + ",".join(missing)], cfg=cfg)

    # S1 safety pre-pass over equipment / level filtered candidates
    pool = sorted(inp.catalog, key=lambda c: c.code)
    req = dataclasses.replace(base, candidates=tuple(c.candidate for c in pool), equipment=tuple(inp.equipment), user_level=inp.level)
    decision = gate.evaluate(req)
    if not decision.status.permits_content:
        return _fail("BLOCKED", ("SAFETY:" + decision.status.value,) + decision.reasons, decision, cfg, decision.flags)
    allowed = set(decision.allowed_codes)
    by_code = {c.code: c for c in pool if c.code in allowed}
    caution = {i.code for i in decision.per_item if i.caution}

    # S2 structure
    n = inp.days_per_week
    structure = inp.preferred_structure if inp.preferred_structure in COMPATIBLE[n] else DEFAULT_STRUCTURE[n]
    if inp.preferred_structure == "custom":
        structure = DEFAULT_STRUCTURE[n]
    reasons = [f"structure:{structure}"] + ([] if inp.preferred_structure in (None, structure) else ["preferred-structure-incompatible"])

    sets, rmin, rmax, rpe, rest = PRESCRIPTION[(inp.goal, _group(inp.level))]
    if inp.recovery_state == "red":
        sets = max(1, sets - 1); reasons.append("recovery:red->sets-1")
    elif inp.recovery_state == "amber":
        reasons.append("recovery:amber")
    used_week: Dict[str, int] = {}
    omissions: List[Omission] = []
    days: List[PlannedDay] = []
    muscle_sets: Dict[str, int] = {}
    alt_used = 0

    for name, slots in _day_names(structure, n):
        chosen: List[PlannedExercise] = []
        day_codes: set = set()
        for slot, pattern, role in slots:
            cands = [c for c in by_code.values() if c.candidate.movement_pattern == pattern and c.code not in day_codes
                     and used_week.get(c.code, 0) < cfg.max_repeat_per_week]
            relaxed = False
            if not cands:
                cands = [c for c in by_code.values() if c.candidate.movement_pattern == pattern and c.code not in day_codes]
                relaxed = bool(cands)                    # content gap: repeat an allowed exercise rather than drop the slot
            if not cands:
                omissions.append(Omission(name, slot, "no-allowed-exercise"))
                continue
            def score(c: CatalogExercise):
                s = (2 if c.role == role else 0) + (1 if c.code in inp.liked_codes else 0)
                if inp.supportive_enabled and set(c.supports_regions) & set(inp.supportive_regions):
                    s += 1.5                       # prefer reviewed supportive exercises; Safety Core already filtered the pool
                s -= 1 if c.code in caution else 0
                s -= used_week.get(c.code, 0)
                s -= 0.5 if c.code in inp.recent_codes else 0     # variety vs recent plans
                return (-s, c.code)                 # stable tie-break by code => deterministic
            best = sorted(cands, key=score)[0]
            if best.role != role or best.code in caution:
                alt_used += 1
            muscle = best.primary_muscle
            if muscle_sets.get(muscle, 0) + sets > cfg.max_weekly_sets_per_muscle[inp.level]:
                omissions.append(Omission(name, slot, "weekly-volume-cap"))
                continue
            muscle_sets[muscle] = muscle_sets.get(muscle, 0) + sets
            used_week[best.code] = used_week.get(best.code, 0) + 1
            day_codes.add(best.code)
            chosen.append(PlannedExercise(best.code, sets if role == "main" else max(2, sets - 1), rmin, rmax, rpe, rest, slot,
                                          "slot-match" + ("+repeat-relaxed" if relaxed else "") + ("+caution" if best.code in caution else "")
                                          + ("+supportive" if inp.supportive_enabled and set(best.supports_regions) & set(inp.supportive_regions) else "")))
        # WO-C01 time budget: drop accessories from the end
        def minutes(ex_list):
            t = cfg.warmup_minutes * 60
            for e in ex_list:
                t += e.sets * (by_code[e.code].default_exec_seconds + e.rest_seconds)
            return -(-t // 60)
        while chosen and minutes(chosen) > inp.session_minutes:
            idx = max((i for i, e in enumerate(chosen) if by_code[e.code].role == "accessory"), default=None)
            if idx is None:
                break
            dropped = chosen.pop(idx)
            omissions.append(Omission(name, dropped.slot, "session-time"))
        # WO-C06 every session needs a main exercise
        if len(chosen) < cfg.min_exercises_per_day or not any(by_code[e.code].role == "main" for e in chosen) or minutes(chosen) > inp.session_minutes:
            return _fail("NEEDS_CONTENT", reasons + [f"WO-C06:{name}"], decision, cfg, decision.flags, omissions)
        order = {s_[0]: i for i, s_ in enumerate(slots)}
        chosen.sort(key=lambda e: (by_code[e.code].role != "main", order[e.slot]))        # main lifts first, then accessories, slot order
        days.append(PlannedDay(name, tuple(chosen), minutes(chosen)))

    # S7 safety post-pass (defence in depth)
    codes = [e.code for d in days for e in d.exercises]
    ok, violations = gate.validate_plan(codes, decision, req)
    if not ok:
        return _fail("ERROR_FAILSAFE", ["SAF-R009"] + list(violations), decision, cfg, decision.flags)

    pp = {"push": 0, "pull": 0}
    for d in days:
        for e in d.exercises:
            k = by_code[e.code].push_pull
            if k in pp:
                pp[k] += e.sets
    flags = list(decision.flags)
    lo, hi = cfg.push_pull_ratio
    if pp["pull"] and pp["push"] and not lo <= pp["push"] / pp["pull"] <= hi or (bool(pp["push"]) != bool(pp["pull"])):
        flags.append("BALANCE_PUSH_PULL")                                                # reported, never silently "fixed" (WO-C03)
    balance = {"weekly_sets_per_muscle": dict(sorted(muscle_sets.items())), "push_sets": pp["push"], "pull_sets": pp["pull"]}
    confidence = "low" if omissions else ("medium" if alt_used else "high")
    return PlanResult(status="OK", days=tuple(days), structure=structure, confidence=confidence,
                      omissions=tuple(omissions), reasons=tuple(reasons), safety_decision_id=decision.decision_id,
                      rule_set_version=decision.rule_set_version, config_version=cfg.version, flags=tuple(flags), balance=balance)


# ---------------------------------------------------------------- progression (DOC-11 §8)
def propose_progression(flags: Sequence[str], sessions: Sequence[Tuple[int, int, float, float]], rep_max: int,
                        rpe_target: float, equipment_kind: str, cfg: EngineConfig, active_pain: bool = False,
                        current_weekly_sets_increase: bool = False):
    """sessions: ordered list of (min_reps_across_sets, sets_completed, load_kg, rpe). Returns dict or None.

    Only one variable changes per step (SAF-R010); locked under PROGRESSION_LOCKED / active pain.
    """
    if "PROGRESSION_LOCKED" in flags or active_pain or len(sessions) < 2:
        return None
    last = sessions[-1]
    if last[0] >= rep_max and last[3] <= rpe_target:
        if current_weekly_sets_increase:
            return None                      # would change two variables at once
        step = cfg.load_step_kg.get(equipment_kind, cfg.load_step_kg["other"])
        return {"action": "increase_load", "new_load_kg": last[2] + step, "reps_reset_to_min": True}
    return None


def should_deload(weeks_since_deload: int, last_two_rpe: Sequence[float], rpe_target: float, cfg: EngineConfig) -> bool:
    if weeks_since_deload >= cfg.deload_every_weeks:
        return True
    return len(last_two_rpe) >= 2 and all(r > rpe_target + 1 for r in last_two_rpe[-2:])

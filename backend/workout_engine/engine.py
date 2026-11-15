"""Deterministic workout plan generator (DOC-11). No LLM. Every exercise passes Safety Core twice."""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Sequence, Tuple

from safety_core import SafetyCore
from safety_core.models import SafetyRequest

from .periodization import adjust, decide_phase
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

# --- movement-assessment integration (heuristic, AI-curated; shapes choices but never approves anything: the Safety Core still gates every code)
DOMAIN_OF = {"squat": "legs", "lunge": "legs", "hinge": "hinge", "push_horizontal": "push", "push_vertical": "push",
             "pull_horizontal": "pull", "pull_vertical": "pull", "core": "core", "rotation": "core", "carry": "core"}
CORRECTIVE = {"ankle_mobility": "ankle_dorsiflexion_rock", "squat_heel_lift": "ankle_dorsiflexion_rock", "overhead_mobility": "wall_slide",
              "posterior_chain_mobility": "wall_hip_hinge", "knee_control": "clamshell"}
UNILATERAL_HINTS = ("single_", "split_squat", "_lunge", "step_up", "pistol", "bulgarian", "skater", "curtsy")
PRIORITY_BUMP = 1.15                     # pattern weight at/above which one extra set is prescribed (inside the weekly volume cap)


def _profile_view(profile):
    """(target level per pattern, extra-set patterns, asymmetry?, limiters) from an assessment profile; empty when absent/untrusted."""
    if not isinstance(profile, dict) or profile.get("method") != "heuristic_v1":
        return {}, set(), False, ()
    levels = {}
    for pat, dom in DOMAIN_OF.items():
        lv = (profile.get("domains", {}).get(dom) or {}).get("level")
        if lv in LEVEL_RANK:
            levels[pat] = lv
    pri = profile.get("priorities", {}) or {}
    bump = {p for p, w in pri.items() if isinstance(w, (int, float)) and w >= PRIORITY_BUMP}
    asym = any(f.get("key", "").endswith("_asymmetry") for f in profile.get("flags", []) or [])
    lim = tuple(x for x in profile.get("limiters", []) or [] if x in CORRECTIVE)
    return levels, bump, asym, lim


# slot = (name, movement_pattern, role). Every day mixes several body regions (never a single-muscle day) and the days of a week rotate
# the emphasis so the whole body is covered; accessories are dropped first when time is short.
FB_A = [("squat", "squat", "main"), ("push_h", "push_horizontal", "main"), ("pull_h", "pull_horizontal", "main"),
        ("hinge", "hinge", "accessory"), ("pull_v", "pull_vertical", "accessory"), ("core", "core", "accessory")]
FB_B = [("hinge", "hinge", "main"), ("push_v", "push_vertical", "main"), ("pull_v", "pull_vertical", "main"),
        ("squat", "squat", "accessory"), ("push_h", "push_horizontal", "accessory"), ("core", "core", "accessory")]
FB_C = [("lunge", "lunge", "main"), ("push_h", "push_horizontal", "main"), ("pull_h", "pull_horizontal", "main"),
        ("squat", "squat", "accessory"), ("hinge", "hinge", "accessory"), ("core", "core", "accessory")]
UPPER_A = [("push_h", "push_horizontal", "main"), ("pull_h", "pull_horizontal", "main"), ("push_v", "push_vertical", "accessory"),
           ("pull_v", "pull_vertical", "accessory"), ("core", "core", "accessory")]
UPPER_B = [("push_v", "push_vertical", "main"), ("pull_v", "pull_vertical", "main"), ("push_h", "push_horizontal", "accessory"),
           ("pull_h", "pull_horizontal", "accessory"), ("core", "core", "accessory")]
LOWER_A = [("squat", "squat", "main"), ("hinge", "hinge", "main"), ("lunge", "lunge", "accessory"), ("core", "core", "accessory")]
LOWER_B = [("hinge", "hinge", "main"), ("lunge", "lunge", "main"), ("squat", "squat", "accessory"), ("core", "core", "accessory")]
PUSH = [("push_h", "push_horizontal", "main"), ("push_v", "push_vertical", "main"), ("squat", "squat", "accessory"), ("core", "core", "accessory")]
PULL = [("pull_h", "pull_horizontal", "main"), ("pull_v", "pull_vertical", "main"), ("hinge", "hinge", "accessory"), ("core", "core", "accessory")]
LEGS = [("squat", "squat", "main"), ("hinge", "hinge", "main"), ("lunge", "lunge", "accessory"), ("pull_h", "pull_horizontal", "accessory"),
        ("core", "core", "accessory")]
# kept for callers/tests that import the old names
FULL_BODY, UPPER, LOWER = FB_A, UPPER_A, LOWER_A

DAY_TEMPLATES = {
    "full_body": [("Full Body A", FB_A), ("Full Body B", FB_B), ("Full Body C", FB_C)],
    "upper_lower": [("Upper A", UPPER_A), ("Lower A", LOWER_A), ("Upper B", UPPER_B), ("Lower B", LOWER_B)],
    "ppl": [("Push", PUSH), ("Pull", PULL), ("Legs", LEGS)],
}
FALLBACK_PATTERN = {"pull_vertical": "pull_horizontal", "push_vertical": "push_horizontal", "lunge": "squat", "squat": "lunge",
                    "pull_horizontal": "pull_vertical", "push_horizontal": "push_vertical"}
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
        res = _generate(inp, base_request, gate)
        if res.status == "NEEDS_CONTENT" and 1 <= inp.days_per_week <= 6:
            # Dead-end guard: the user's equipment cannot fill the preferred split -> try the other structures before giving up (DEC-160).
            first = next((r[10:] for r in res.reasons if r.startswith("structure:")), None)
            for alt in dict.fromkeys(list(COMPATIBLE[inp.days_per_week]) + ["full_body", "ppl", "upper_lower"]):
                if alt == first or alt not in DAY_TEMPLATES:
                    continue
                r2 = _generate(inp, base_request, gate, force_structure=alt)
                if r2.status == "OK":
                    return dataclasses.replace(r2, reasons=r2.reasons + (f"structure-fallback:{first}->{alt}",), confidence="low" if r2.confidence is None else r2.confidence)
        return res
    except Exception as exc:  # noqa: BLE001
        return _fail("ERROR_FAILSAFE", ("WO-ERR", type(exc).__name__), cfg=getattr(inp, "config", None))


def _generate(inp: EngineInput, base: SafetyRequest, gate: SafetyCore, force_structure=None) -> PlanResult:
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
    structure = force_structure or (inp.preferred_structure if inp.preferred_structure in COMPATIBLE[n] else DEFAULT_STRUCTURE[n])
    if inp.preferred_structure == "custom":
        structure = DEFAULT_STRUCTURE[n]
    reasons = [f"structure:{structure}"] + ([] if inp.preferred_structure in (None, structure) else ["preferred-structure-incompatible"])

    sets, rmin, rmax, rpe, rest = PRESCRIPTION[(inp.goal, _group(inp.level))]
    if inp.recovery_state == "red":
        sets = max(1, sets - 1); reasons.append("recovery:red->sets-1")
    elif inp.recovery_state == "amber":
        reasons.append("recovery:amber")
    phase, phase_reasons = decide_phase(inp.block_week, inp.load_signals, cfg.block_weeks)
    if phase != "standard":
        sets, rpe = adjust(phase, sets, rpe, cfg.deload_factor)
        reasons.extend(phase_reasons)
    p_levels, p_bump, p_asym, p_limiters = _profile_view(inp.profile)
    if phase in ("deload", "reentry"):
        p_bump = ()                                  # no extra weak-area sets while easing off
    if p_levels or p_limiters:
        reasons.append("profile:heuristic_v1")
    used_week: Dict[str, int] = {}
    omissions: List[Omission] = []
    days: List[PlannedDay] = []
    muscle_sets: Dict[str, int] = {}
    alt_used = 0

    for name, slots in _day_names(structure, n):
        chosen: List[PlannedExercise] = []
        day_codes: set = set()
        day_muscles: set = set()
        for slot, pattern, role in slots:
            def pool_for(pat: str):
                fresh = [c for c in by_code.values() if c.candidate.movement_pattern == pat and c.code not in day_codes
                         and used_week.get(c.code, 0) < cfg.max_repeat_per_week]
                return fresh, [c for c in by_code.values() if c.candidate.movement_pattern == pat and c.code not in day_codes]
            cands, anyc = pool_for(pattern)
            relaxed = False
            if not cands and anyc:
                cands, relaxed = anyc, True                  # content gap: repeat an allowed exercise rather than drop the slot
            if not cands and pattern in FALLBACK_PATTERN:    # nothing for this pattern with the user's equipment: use the sibling pattern (e.g. vertical -> horizontal pull)
                fb_fresh, fb_any = pool_for(FALLBACK_PATTERN[pattern])
                cands = fb_fresh or fb_any
                relaxed = bool(cands)
                if cands:
                    reasons.append(f"pattern-fallback:{name}:{pattern}->{FALLBACK_PATTERN[pattern]}")
            if not cands:
                omissions.append(Omission(name, slot, "no-allowed-exercise"))
                continue
            def score(c: CatalogExercise):
                s = (2 if c.role == role else 0) + (1 if c.code in inp.liked_codes else 0)
                if inp.supportive_enabled and set(c.supports_regions) & set(inp.supportive_regions):
                    s += 1.5                       # prefer reviewed supportive exercises; Safety Core already filtered the pool
                s += 0.75 if c.primary_muscle in inp.priority_muscles else 0     # user focus: preference only
                s -= 1 if c.code in caution else 0
                s += 0.8 if c.primary_muscle not in day_muscles else 0     # variety inside the day: cover more different muscles
                s -= used_week.get(c.code, 0)
                s -= 0.5 if c.code in inp.recent_codes else 0     # variety vs recent plans
                tgt = p_levels.get(pattern)
                if tgt is not None:                                # match exercise difficulty to the user's tested level in this pattern
                    gap = LEVEL_RANK[c.candidate.difficulty] - LEVEL_RANK[tgt]
                    s -= 2.0 * gap if gap > 0 else 0.4 * -gap
                if p_asym and any(h in c.code for h in UNILATERAL_HINTS):
                    s += 0.6                                       # asymmetry found: prefer single-side work
                return (-s, c.code)                 # stable tie-break by code => deterministic
            ranked = sorted(cands, key=score)
            cap = cfg.max_weekly_sets_per_muscle[inp.level]
            best = ranked[0]
            muscle = best.primary_muscle
            eff_sets = sets + 1 if pattern in p_bump else sets          # weaker pattern -> one extra set (never past the cap)
            if muscle_sets.get(muscle, 0) + eff_sets > cap:
                eff_sets = sets
            if muscle_sets.get(muscle, 0) + eff_sets > cap:
                # prefer another candidate whose muscle still has room, then fewer sets, and only then omit the slot
                alt = next((c for c in ranked if muscle_sets.get(c.primary_muscle, 0) + sets <= cap), None)
                if alt is not None:
                    best, muscle, eff_sets = alt, alt.primary_muscle, sets
                elif muscle_sets.get(muscle, 0) + 2 <= cap:
                    eff_sets = 2
                else:
                    omissions.append(Omission(name, slot, "weekly-volume-cap"))
                    continue
            if best.role != role or best.code in caution:
                alt_used += 1
            muscle_sets[muscle] = muscle_sets.get(muscle, 0) + eff_sets
            used_week[best.code] = used_week.get(best.code, 0) + 1
            day_codes.add(best.code)
            day_muscles.add(best.primary_muscle)
            n_sets = eff_sets if role == "main" else max(2, eff_sets - 1)
            chosen.append(PlannedExercise(best.code, n_sets, rmin, rmax, rpe, rest, slot,
                                          "slot-match" + ("+repeat-relaxed" if relaxed else "") + ("+caution" if best.code in caution else "")
                                          + ("+extra-set:weak-area" if eff_sets > sets else "")
                                          + (f"+level:{p_levels[pattern]}" if pattern in p_levels else "")
                                          + ("+supportive" if inp.supportive_enabled and set(best.supports_regions) & set(inp.supportive_regions) else "")
                                          + ("+priority" if best.primary_muscle in inp.priority_muscles else "")))
        # WO-C01 time budget: drop accessories from the end
        def minutes(ex_list):
            t = cfg.warmup_minutes * 60
            for e in ex_list:
                t += e.sets * (by_code[e.code].default_exec_seconds + e.rest_seconds)
            return -(-t // 60)
        min_ex = cfg.min_exercises_per_day if inp.session_minutes >= 40 else max(2, cfg.min_exercises_per_day - 1)   # short sessions: 2 well-chosen moves beat no plan
        while len(chosen) > min_ex and minutes(chosen) > inp.session_minutes:
            idx = max((i for i, e in enumerate(chosen) if by_code[e.code].role == "accessory"), default=None)
            if idx is None:
                break
            dropped = chosen.pop(idx)
            omissions.append(Omission(name, dropped.slot, "session-time"))
        if minutes(chosen) > inp.session_minutes:           # still too long: ease the prescription instead of failing (fewer sets, shorter rests)
            for rest_cap, set_floor in ((75, 3), (60, 2), (45, 2)):
                chosen = [dataclasses.replace(e, rest_seconds=min(e.rest_seconds, rest_cap), sets=max(min(e.sets, set_floor), 2) if e.sets > set_floor else e.sets) for e in chosen]
                if minutes(chosen) <= inp.session_minutes:
                    break
            if minutes(chosen) <= inp.session_minutes:
                reasons.append(f"time-fit:{name}")
        # WO-C06 (amended, DEC-160): a session needs >= min_ex exercises; when the user's equipment offers no 'main'-role move the most demanding
        # chosen exercise anchors the day and the plan says so, instead of failing (a labelled lighter plan beats a dead end).
        if chosen and not any(by_code[e.code].role == "main" for e in chosen):
            reasons.append(f"no-main-available:{name}")
        if len(chosen) < min_ex or minutes(chosen) > inp.session_minutes:
            return _fail("NEEDS_CONTENT", reasons + [f"WO-C06:{name}"], decision, cfg, decision.flags, omissions)
        order = {s_[0]: i for i, s_ in enumerate(slots)}
        chosen.sort(key=lambda e: (by_code[e.code].role != "main", order[e.slot]))        # main lifts first, then accessories, slot order
        if p_limiters:                                   # one corrective drill per session (rotating), only if allowed and it fits the time budget
            lim = p_limiters[len(days) % len(p_limiters)]
            code = CORRECTIVE[lim]
            if code in by_code and code not in day_codes:
                corr = PlannedExercise(code, 2, 8, 12, 3.0, 30, "corrective", f"corrective:{lim}")
                if minutes([corr] + chosen) <= inp.session_minutes:
                    chosen.insert(0, corr)
                    reasons.append(f"corrective:{lim}:{code}")
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

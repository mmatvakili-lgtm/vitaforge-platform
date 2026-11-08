"""History-based, explainable progression & recovery (DOC-11 §8). Heuristics are engineering defaults, NOT clinical advice (EXP-013).

Every decision returns: action, params, reasons (human-readable codes) and the evidence facts that triggered it.
Never changes two variables at once; never progresses under pain / locked flags / poor adherence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .models import EngineConfig


@dataclass(frozen=True)
class SetLog:
    reps: int
    load_kg: float
    rpe: Optional[float] = None


@dataclass(frozen=True)
class SessionPerf:
    day: int
    sets: Tuple[SetLog, ...]
    planned_sets: int
    rep_min: int
    rep_max: int
    completed: bool = True
    pain_reported: bool = False
    fatigue: Optional[int] = None              # user-reported 1..10


@dataclass(frozen=True)
class ProgressionConfig:
    min_sessions: int = 2
    adherence_window: int = 3
    min_adherence: float = 0.6
    stall_window: int = 3
    reduce_load_factor: float = 0.9
    fatigue_hold_threshold: int = 8
    pain_reassess_count: int = 2
    rpe_target: float = 7.5


@dataclass(frozen=True)
class ProgressionDecision:
    action: str            # increase_load | increase_reps | hold | reduce_load | suggest_deload | pause_pain | locked | insufficient_data
    params: Dict[str, float] = field(default_factory=dict)
    reasons: Tuple[str, ...] = ()
    evidence: Dict[str, object] = field(default_factory=dict)
    flags: Tuple[str, ...] = ()
    confidence: str = "low"


def _e1rm(s: SetLog) -> float:
    return s.load_kg * (1 + s.reps / 30.0)       # Epley estimate: used only to compare sessions of the same exercise


def _best(sp: SessionPerf) -> float:
    return max((_e1rm(s) for s in sp.sets), default=0.0)


def decide(history: Sequence[SessionPerf], flags: Sequence[str], equipment_kind: str, cfg: EngineConfig,
           pcfg: ProgressionConfig = ProgressionConfig(), weekly_volume_change_pending: bool = False) -> ProgressionDecision:
    h = sorted(history, key=lambda x: x.day)
    if "PROGRESSION_LOCKED" in flags:
        return ProgressionDecision("locked", reasons=("flag:PROGRESSION_LOCKED",), confidence="high")
    done = [x for x in h if x.completed and x.sets]
    if h and h[-1].pain_reported:
        recent_pain = sum(1 for x in h[-3:] if x.pain_reported)
        fl = ("REASSESSMENT_RECOMMENDED",) if recent_pain >= pcfg.pain_reassess_count else ()
        return ProgressionDecision("pause_pain", reasons=("pain-reported-last-session",) + (("repeated-pain",) if fl else ()),
                                   evidence={"pain_sessions_last3": recent_pain}, flags=fl, confidence="high")
    if len(done) < pcfg.min_sessions:
        return ProgressionDecision("insufficient_data", reasons=("fewer-than-min-sessions",), evidence={"sessions": len(done)})
    window = h[-pcfg.adherence_window:]
    adherence = sum(1 for x in window if x.completed and len(x.sets) >= x.planned_sets) / len(window)
    if adherence < pcfg.min_adherence:
        return ProgressionDecision("hold", reasons=("low-adherence",), evidence={"adherence": round(adherence, 2)}, confidence="medium")
    last = done[-1]
    fat = [x.fatigue for x in done[-2:] if x.fatigue is not None]
    if len(fat) == 2 and all(f >= pcfg.fatigue_hold_threshold for f in fat):
        return ProgressionDecision("suggest_deload", params={"factor": cfg.deload_factor}, reasons=("high-fatigue-2-sessions",),
                                   evidence={"fatigue": fat}, confidence="medium")
    low = [x for x in done[-2:] if min(s.reps for s in x.sets) < x.rep_min]
    if len(low) == 2 and len({s.load_kg for x in low for s in x.sets}) == 1:
        load = last.sets[-1].load_kg
        return ProgressionDecision("reduce_load", params={"new_load_kg": round(load * pcfg.reduce_load_factor, 1)},
                                   reasons=("below-rep-floor-2-sessions",), evidence={"load_kg": load}, confidence="medium")
    if len(done) > pcfg.stall_window:
        bests = [_best(x) for x in done[-(pcfg.stall_window + 1):]]
        if max(bests[1:]) <= bests[0] and not all(b == 0 for b in bests):
            return ProgressionDecision("suggest_deload", params={"factor": cfg.deload_factor}, reasons=("stalled-no-improvement",),
                                       evidence={"e1rm_window": [round(b, 1) for b in bests]}, flags=("STALLED",), confidence="low")
    at_top = all(s.reps >= last.rep_max for s in last.sets) and len(last.sets) >= last.planned_sets
    rpes = [s.rpe for s in last.sets if s.rpe is not None]
    easy = bool(rpes) and max(rpes) <= pcfg.rpe_target
    if at_top and easy:
        if weekly_volume_change_pending:
            return ProgressionDecision("hold", reasons=("one-variable-at-a-time",), confidence="high")
        step = cfg.load_step_kg.get(equipment_kind, cfg.load_step_kg["other"])
        return ProgressionDecision("increase_load", params={"new_load_kg": last.sets[-1].load_kg + step, "reps_reset_to": last.rep_min},
                                   reasons=("top-of-range-and-rpe-ok",), evidence={"rpe_max": max(rpes)}, confidence="medium")
    if not at_top and easy and len(last.sets) >= last.planned_sets:
        return ProgressionDecision("increase_reps", params={"target_reps": min(last.rep_max, min(s.reps for s in last.sets) + 1)},
                                   reasons=("within-range-rpe-ok",), evidence={"rpe_max": max(rpes)}, confidence="medium")
    return ProgressionDecision("hold", reasons=("no-progression-criteria-met",), confidence="medium")


# ---------------------------------------------------------------- recovery
@dataclass(frozen=True)
class RecoveryInput:
    sessions_last7: int
    sessions_planned_last7: int
    avg_fatigue: Optional[float] = None        # 1..10 user-reported
    avg_soreness: Optional[float] = None       # 1..10
    sleep_hours_avg: Optional[float] = None
    pain_reports_last7: int = 0


@dataclass(frozen=True)
class RecoveryAssessment:
    state: str                                  # green | amber | red | unknown
    reasons: Tuple[str, ...]
    uncertainty: str = "high"                   # self-report based; never "low"


def assess_recovery(r: RecoveryInput) -> RecoveryAssessment:
    known = [x for x in (r.avg_fatigue, r.avg_soreness, r.sleep_hours_avg) if x is not None]
    if not known and r.pain_reports_last7 == 0:
        return RecoveryAssessment("unknown", ("no-self-report-data",))
    reasons: List[str] = []
    red = amber = 0
    if r.pain_reports_last7 >= 2: red += 1; reasons.append("pain-reports>=2")
    elif r.pain_reports_last7 == 1: amber += 1; reasons.append("pain-report-1")
    if r.avg_fatigue is not None:
        if r.avg_fatigue >= 8: red += 1; reasons.append("fatigue>=8")
        elif r.avg_fatigue >= 6: amber += 1; reasons.append("fatigue>=6")
    if r.avg_soreness is not None:
        if r.avg_soreness >= 8: red += 1; reasons.append("soreness>=8")
        elif r.avg_soreness >= 6: amber += 1; reasons.append("soreness>=6")
    if r.sleep_hours_avg is not None and r.sleep_hours_avg < 5.5: amber += 1; reasons.append("sleep<5.5h")
    if r.sessions_planned_last7 and r.sessions_last7 > r.sessions_planned_last7: amber += 1; reasons.append("more-sessions-than-planned")
    state = "red" if red else ("amber" if amber >= 1 else "green")
    return RecoveryAssessment(state, tuple(reasons) or ("no-risk-signals",), uncertainty="medium" if len(known) >= 2 else "high")

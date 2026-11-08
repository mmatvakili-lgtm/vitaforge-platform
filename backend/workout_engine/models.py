"""Workout Engine domain models (pure Python, no Django)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from safety_core.models import ExerciseCandidate, SafetyDecision

GOALS = ("strength", "muscle_gain", "general_fitness", "fat_loss")
LEVELS = ("beginner", "intermediate", "advanced")
LEVEL_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}
STRUCTURES = ("full_body", "upper_lower", "ppl", "custom")


@dataclass(frozen=True)
class CatalogExercise:
    """Safety-tagged candidate plus the planning attributes the engine needs."""
    candidate: ExerciseCandidate
    role: str                      # main | accessory
    primary_muscle: str
    push_pull: Optional[str] = None  # push | pull | None
    default_exec_seconds: int = 40
    supports_regions: Tuple[str, ...] = ()   # reviewed 'supportive' tag; only used when supportive content is published

    @property
    def code(self) -> str:
        return self.candidate.code


@dataclass(frozen=True)
class EngineConfig:
    """Technical defaults, NOT clinical advice (DOC-11, EXP-013). Versioned."""
    version: int = 1
    status: str = "unverified"
    warmup_minutes: int = 5
    max_repeat_per_week: int = 2
    min_exercises_per_day: int = 3          # fewer => NEEDS_CONTENT (a 1-exercise 'plan' would be misleading)
    max_weekly_sets_per_muscle: Mapping[str, int] = field(default_factory=lambda: {"beginner": 12, "intermediate": 16, "advanced": 20})
    push_pull_ratio: Tuple[float, float] = (0.5, 2.0)
    load_step_kg: Mapping[str, float] = field(default_factory=lambda: {"barbell": 2.5, "dumbbell": 2.0, "machine": 2.5, "other": 1.0})
    deload_every_weeks: int = 6
    deload_factor: float = 0.6


@dataclass(frozen=True)
class EngineInput:
    user_id: str
    goal: str
    level: str
    days_per_week: int
    session_minutes: int
    equipment: Tuple[str, ...]
    catalog: Tuple[CatalogExercise, ...]
    preferred_structure: Optional[str] = None
    liked_codes: Tuple[str, ...] = ()
    recent_codes: Tuple[str, ...] = ()          # exercises used in recent plans -> variety
    recovery_state: Optional[str] = None        # green | amber | red (from progression.assess_recovery)
    supportive_regions: Tuple[str, ...] = ()   # regions with a recorded history and NO active pain (Path A)
    supportive_enabled: bool = False           # True only when reviewed supportive content is published
    config: EngineConfig = field(default_factory=EngineConfig)


@dataclass(frozen=True)
class PlannedExercise:
    code: str
    sets: int
    reps_min: int
    reps_max: int
    rpe: float
    rest_seconds: int
    slot: str
    reason: str


@dataclass(frozen=True)
class PlannedDay:
    name: str
    exercises: Tuple[PlannedExercise, ...]
    estimated_minutes: int


@dataclass(frozen=True)
class Omission:
    day: str
    slot: str
    reason: str


@dataclass(frozen=True)
class PlanResult:
    status: str                    # OK | NEEDS_INFO | NEEDS_CONTENT | BLOCKED | ERROR_FAILSAFE
    days: Tuple[PlannedDay, ...] = ()
    structure: Optional[str] = None
    confidence: Optional[str] = None
    omissions: Tuple[Omission, ...] = ()
    reasons: Tuple[str, ...] = ()
    safety_decision_id: Optional[str] = None
    rule_set_version: Optional[int] = None
    config_version: Optional[int] = None
    flags: Tuple[str, ...] = ()
    balance: Mapping[str, Any] = field(default_factory=dict)   # weekly sets per muscle, push/pull sets
    label: str = "experimental"    # shown in UI until EXP-013 closes

    @property
    def codes(self) -> Tuple[str, ...]:
        return tuple(e.code for d in self.days for e in d.exercises)

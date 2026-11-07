"""Domain models for the Safety Core (pure Python; no Django / HTTP / LLM imports).

Contracts follow docs/03-ai-safety/09-safety-clinical-governance.md.
All models are immutable value objects so decisions are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Tuple

REGIONS: Tuple[str, ...] = (
    "lower_back", "spine_other", "neck", "mid_back", "shoulder", "elbow", "wrist",
    "hand", "hip", "groin", "knee", "ankle", "foot", "muscle_tendon", "other",
)
LOADINGS: Tuple[str, ...] = ("none", "low", "moderate", "high")
LOADING_RANK = {name: i for i, name in enumerate(LOADINGS)}
CONDITION_STATUSES: Tuple[str, ...] = (
    "no_known_limitation", "self_reported_symptom", "professionally_assessed",
    "active_professional_restriction", "cleared_to_return", "needs_reassessment",
    "needs_urgent_referral",
)
PROBLEM_TYPES: Tuple[str, ...] = ("pain", "limited_motion", "diagnosed_injury", "surgery_history", "other")
SOURCES: Tuple[str, ...] = ("self_reported", "professional")
OUT_OF_SCOPE_TYPES: Tuple[str, ...] = ("pregnancy", "high_risk_condition", "other")


class DecisionStatus(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_MODIFICATION = "ALLOW_WITH_MODIFICATION"
    RESTRICT = "RESTRICT"
    NEEDS_INFO = "NEEDS_INFO"
    STOP_AND_REFER = "STOP_AND_REFER"
    BLOCK_OUT_OF_SCOPE = "BLOCK_OUT_OF_SCOPE"
    BLOCK_CONSENT = "BLOCK_CONSENT"
    ERROR_FAILSAFE = "ERROR_FAILSAFE"

    @property
    def permits_content(self) -> bool:
        return self in (DecisionStatus.ALLOW, DecisionStatus.ALLOW_WITH_MODIFICATION)


@dataclass(frozen=True)
class RegionLoad:
    region: str
    loading: str


@dataclass(frozen=True)
class ExerciseCandidate:
    """Exercise as seen by the Safety Core (already loaded by the catalog module)."""
    code: str
    review_status: str                       # draft|scientific_review|safety_review|published|retired
    safety_tags_complete: bool
    movement_pattern: str
    region_loads: Tuple[RegionLoad, ...] = ()
    contraindications: Tuple[Tuple[str, Optional[str]], ...] = ()   # (code, region|None)
    cautions: Tuple[Tuple[str, Optional[str]], ...] = ()
    difficulty: str = "beginner"
    equipment: Tuple[str, ...] = ()

    def loading_for(self, region: str) -> Optional[str]:
        for rl in self.region_loads:
            if rl.region == region:
                return rl.loading
        return None


@dataclass(frozen=True)
class Condition:
    region: str
    problem_type: str
    status: str
    source: str = "self_reported"
    active_pain: bool = False
    worsening: bool = False


@dataclass(frozen=True)
class Restriction:
    """Structured professional restriction (hard filter)."""
    region: Optional[str] = None
    movement_pattern: Optional[str] = None
    exercise_code: Optional[str] = None
    max_loading: Optional[str] = None        # none|low|moderate|None => 'none' (conservative)
    valid_until_ordinal: Optional[int] = None  # date.toordinal(); None = no expiry


@dataclass(frozen=True)
class OutOfScopeFlag:
    flag_type: str
    active: bool = True


@dataclass(frozen=True)
class SafetyRequest:
    user_id: str
    age_years: Optional[int]
    consent_health_valid: Optional[bool]
    red_flag_answers: Mapping[str, Optional[bool]]      # key -> True (positive) / False / None (unanswered)
    out_of_scope_flags: Tuple[OutOfScopeFlag, ...] = ()
    conditions: Tuple[Condition, ...] = ()
    restrictions: Tuple[Restriction, ...] = ()
    candidates: Tuple[ExerciseCandidate, ...] = ()
    today_ordinal: int = 0
    context: Mapping[str, Any] = field(default_factory=dict)
    context_type: str = "plan_generation"


@dataclass(frozen=True)
class ClinicalRule:
    """Data-driven rule (JSON-logic subset). Clinical rules start as draft_unreviewed."""
    code: str
    name: str
    stage: int
    condition: Any
    action: Mapping[str, Any]
    severity: str = "high"
    review_status: str = "draft_unreviewed"          # draft_unreviewed|clinical_reviewed|published
    source_ref: Optional[str] = None
    is_structural: bool = False


@dataclass(frozen=True)
class RuleSet:
    version: int
    status: str = "draft_unreviewed"                 # draft_unreviewed|clinical_reviewed|published|retired
    adult_age: int = 18
    screening_questions: Tuple[str, ...] = ()        # required red-flag question keys (EXP-001; draft)
    clinical_content_published: bool = False         # reviewed red-flag list + referral texts available?
    allow_unreviewed_content: bool = False           # True only in dev/test environments
    path_b_activity_rules_published: bool = False    # EXP-011 reviewed B4 rules available?
    caution_max_loading: str = "none"                # self-reported-only regions: conservative default
    reviewed_flag_urgency: str = "non_urgent"        # urgency when a red flag is positive (EXP-001 refines)
    path_b_related_regions: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()   # EXP-003 mapping region -> related regions
    clinical_rules: Tuple[ClinicalRule, ...] = ()


@dataclass(frozen=True)
class ItemResult:
    code: str
    allowed: bool
    reasons: Tuple[str, ...] = ()
    caution: bool = False


@dataclass(frozen=True)
class SafetyDecision:
    decision_id: str
    status: DecisionStatus
    per_item: Tuple[ItemResult, ...]
    reasons: Tuple[str, ...]
    required_questions: Tuple[str, ...]
    referral_urgency: Optional[str]                   # urgent|non_urgent|None
    rule_set_version: int
    inputs_hash: str
    content_status: str                               # draft_unreviewed|published
    pathway: Optional[str] = None                     # A|B|None (C is blocked_expert, Deferred)
    flags: Tuple[str, ...] = ()                       # e.g. PROGRESSION_LOCKED, REASSESSMENT_RECOMMENDED

    @property
    def allowed_codes(self) -> Tuple[str, ...]:
        if not self.status.permits_content:
            return ()
        return tuple(i.code for i in self.per_item if i.allowed)

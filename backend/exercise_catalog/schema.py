"""Exercise record schema (DOC-10) with provenance and review state. Unsourced facts are never 'verified'."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

from safety_core.models import LOADINGS, REGIONS

PUBLICATION_STATUSES = ("draft", "experimental", "pending_review", "scientific_review", "safety_review", "published", "retired")
EXPERT_STATUSES = ("none", "pending", "approved", "rejected")
LEVELS = ("beginner", "intermediate", "advanced")
EXERCISE_TYPES = ("strength", "mobility", "stability", "cardio", "plyometric", "stretching")
CONTRACTIONS = ("concentric_eccentric", "isometric", "concentric", "eccentric", "unspecified")
PATTERNS = ("squat", "hinge", "push_horizontal", "push_vertical", "pull_horizontal", "pull_vertical", "lunge", "core", "carry", "rotation", "other")
EVIDENCE = ("none", "expert_opinion", "guideline", "systematic_review")


@dataclass(frozen=True)
class SourceRef:
    source_id: str                      # key in sources registry
    reference: str = ""                 # citation / URL / file id
    license_ok_for_commercial: Optional[bool] = None   # None = unverified


@dataclass(frozen=True)
class ExerciseRecord:
    id: str
    name_en: str
    name_fa: Optional[str] = None
    aliases: Tuple[str, ...] = ()
    description: str = ""
    primary_muscles: Tuple[str, ...] = ()
    secondary_muscles: Tuple[str, ...] = ()
    movement_pattern: str = "other"
    exercise_type: str = "strength"
    equipment: Tuple[str, ...] = ()
    difficulty: str = "beginner"
    contraction: str = "unspecified"
    range_of_motion: str = ""
    instructions: Tuple[str, ...] = ()
    common_mistakes: Tuple[str, ...] = ()
    contraindications: Tuple[Tuple[str, Optional[str]], ...] = ()      # (code, region)
    cautions: Tuple[Tuple[str, Optional[str]], ...] = ()
    alternatives: Tuple[str, ...] = ()
    regressions: Tuple[str, ...] = ()
    region_loads: Dict[str, str] = field(default_factory=dict)         # safety tags: region -> loading
    safety_tags_status: str = "missing"                                  # missing | unreviewed_estimate | reviewed
    publication_status: str = "draft"
    sources: Tuple[SourceRef, ...] = ()
    evidence_level: str = "none"
    last_reviewed: Optional[date] = None
    expert_review: str = "none"
    is_sample: bool = False
    role: str = "accessory"             # main | accessory (planning attribute)
    push_pull: Optional[str] = None
    supports_regions: Tuple[str, ...] = ()   # 'supportive' tag; only meaningful once reviewed (OPEN-008)


def validate_record(r: ExerciseRecord) -> List[str]:
    """Structural validation only. Says nothing about scientific correctness."""
    p: List[str] = []
    if not r.id or not r.name_en:
        p.append("id/name_en required")
    if r.publication_status not in PUBLICATION_STATUSES: p.append("publication_status")
    if r.expert_review not in EXPERT_STATUSES: p.append("expert_review")
    if r.difficulty not in LEVELS: p.append("difficulty")
    if r.exercise_type not in EXERCISE_TYPES: p.append("exercise_type")
    if r.contraction not in CONTRACTIONS: p.append("contraction")
    if r.movement_pattern not in PATTERNS: p.append("movement_pattern")
    if r.evidence_level not in EVIDENCE: p.append("evidence_level")
    if any(reg not in REGIONS or ld not in LOADINGS for reg, ld in r.region_loads.items()): p.append("region_loads values")
    if r.safety_tags_status not in ("missing", "unreviewed_estimate", "reviewed"): p.append("safety_tags_status")
    if r.safety_tags_status != "missing" and set(r.region_loads) != set(REGIONS): p.append("region_loads must cover all regions")
    if r.evidence_level != "none" and not r.sources: p.append("evidence_level without sources")
    return p


def publication_blockers(r: ExerciseRecord) -> List[str]:
    """Everything that currently prevents publishing. Empty list == publishable (still needs the human sign-off workflow)."""
    b = validate_record(r)
    if r.is_sample: b.append("sample content")
    if r.expert_review != "approved": b.append("expert review not approved")
    if r.safety_tags_status != "reviewed": b.append("safety tags not reviewed")
    if not r.sources: b.append("no source")
    if any(s.license_ok_for_commercial is not True for s in r.sources): b.append("source license not confirmed for commercial use")
    if not r.instructions: b.append("no instructions")
    if r.last_reviewed is None: b.append("no review date")
    if not r.primary_muscles: b.append("no primary muscles")
    return b

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
LICENSE_STATUSES = ("project_authored", "third_party_verified", "third_party_unverified", "restricted", "unknown")
# Controlled vocabularies (standardisation). Checked as PUBLICATION blockers, not structural errors, so raw imports can still be stored.
ENVIRONMENTS = ("home", "gym", "outdoor")
MEDIA_KINDS = ("image", "video")
MUSCLES = ("abductors", "adductors", "middle back", "neck", "abdominals", "anterior deltoid", "posterior deltoid", "biceps", "calves", "chest", "core", "deltoids", "erector spinae", "forearms",
           "glutes", "hamstrings", "hip flexors", "lats", "lower back", "lower trapezius", "middle trapezius", "obliques", "quadriceps",
           "rhomboids", "shoulders", "trapezius", "triceps")
EQUIPMENT = ("dumbbell", "barbell", "bench", "box", "band", "machine", "kettlebell", "pull_up_bar", "cable")   # bodyweight == empty tuple


@dataclass(frozen=True)
class SourceRef:
    source_id: str                      # key in sources registry
    reference: str = ""                 # citation / URL / file id
    license_ok_for_commercial: Optional[bool] = None   # None = unverified


@dataclass(frozen=True)
class MediaRef:
    """Reference to an image/video. Never served unless its own licence is confirmed (see served_media); the file itself is not stored here."""
    kind: str                           # image | video
    url: str
    license: str = "unknown"            # SPDX-like id or 'unknown'
    license_verified: bool = False
    attribution: str = ""
    source_id: str = ""


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
    limitations: Tuple[str, ...] = ()       # human-readable limits of THIS record/movement (display only; NOT a safety decision — Safety Core uses cautions/contraindications codes)
    license_status: str = "unknown"         # provenance of the TEXT of this record (see sources for per-source detail)
    review_notes: Tuple[str, ...] = ()      # open points a reviewer must resolve; any open note blocks publication
    starting_position: str = ""             # setup text; empty == not provided (never inferred)
    breathing: str = ""
    progressions: Tuple[str, ...] = ()      # ids of harder variations (regressions = easier)
    environments: Tuple[str, ...] = ()      # home | gym | outdoor (empty == unknown)
    media: Tuple[MediaRef, ...] = ()
    safety_cautions: Tuple[str, ...] = ()   # display text; the Safety Core uses the coded cautions/contraindications only
    source_published: Optional[str] = None  # publication/retrieval date of the primary source (ISO date string)
    source_quality: str = "unverified"      # unverified | community | peer_reviewed | guideline
    evidence_limitations: str = ""


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
    if r.license_status not in LICENSE_STATUSES: p.append("license_status")
    if any(e not in ENVIRONMENTS for e in r.environments): p.append("environments")
    if any(m.kind not in MEDIA_KINDS or not m.url for m in r.media): p.append("media")
    if any(m.license_verified and m.license in ("", "unknown") for m in r.media): p.append("media license_verified without a licence")
    if any(not (isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], str)) for x in r.cautions + r.contraindications): p.append("cautions/contraindications must be (code, region) pairs")
    if r.license_status == "third_party_verified" and (not r.sources or any(s.license_ok_for_commercial is not True for s in r.sources)):
        p.append("license_status third_party_verified without confirmed source licenses")
    if r.safety_tags_status == "missing" and r.region_loads: p.append("region_loads present but safety_tags_status is 'missing' (label estimates 'unreviewed_estimate')")
    if r.safety_tags_status == "reviewed" and r.expert_review != "approved": p.append("safety tags marked reviewed without approved expert review")
    if "bodyweight" in r.equipment and len(r.equipment) > 1: p.append("bodyweight cannot be combined with other equipment")
    if r.publication_status == "published":
        gate = _gate_blockers(r)
        if gate: p.append("published but blocked: " + "; ".join(gate))
    return p


def _gate_blockers(r: ExerciseRecord) -> List[str]:
    b: List[str] = []
    if r.is_sample: b.append("sample content")
    if r.expert_review != "approved": b.append("expert review not approved")
    if r.safety_tags_status != "reviewed": b.append("safety tags not reviewed")
    if not r.sources: b.append("no source")
    if any(s.license_ok_for_commercial is not True for s in r.sources): b.append("source license not confirmed for commercial use")
    if not r.instructions: b.append("no instructions")
    if r.last_reviewed is None: b.append("no review date")
    if not r.primary_muscles: b.append("no primary muscles")
    if r.license_status not in ("project_authored", "third_party_verified"): b.append("license status not confirmed")
    if r.review_notes: b.append("open review notes")
    if any(m not in MUSCLES for m in r.primary_muscles + r.secondary_muscles): b.append("muscle names outside controlled vocabulary")
    if any(e not in EQUIPMENT and e != "bodyweight" for e in r.equipment): b.append("equipment outside controlled vocabulary")
    return b


def publication_blockers(r: ExerciseRecord) -> List[str]:
    """Everything that currently prevents publishing. Empty list == publishable (still needs the human sign-off workflow)."""
    return validate_record(r) + _gate_blockers(r)


def served_media(r: ExerciseRecord) -> Tuple[MediaRef, ...]:
    """Only media whose own licence is verified may be shown to users."""
    return tuple(m for m in r.media if m.license_verified)

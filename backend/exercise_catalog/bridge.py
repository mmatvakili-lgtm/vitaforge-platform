"""ExerciseRecord -> Safety Core candidate / Workout Engine catalog entry. Production never lifts review gates."""
from __future__ import annotations

import os

from safety_core.models import REGIONS, ExerciseCandidate, RegionLoad
from workout_engine.models import CatalogExercise

from .schema import ExerciseRecord, publication_blockers


class ProductionCatalogError(Exception):
    pass


def ai_curated_demo_acknowledged() -> bool:
    """The only way unreviewed content may run with VITAFORGE_ENV=production: the explicit public-demo mode AND its acknowledgement."""
    return (os.environ.get("VITAFORGE_CONTENT_MODE", "").strip().lower() == "ai_curated_demo"
            and os.environ.get("VITAFORGE_ACK_AI_CURATED_CONTENT", "").strip().lower() == "yes")


def to_candidate(r: ExerciseRecord, dev_experimental: bool = False) -> ExerciseCandidate:
    """In production only `published` + reviewed tags pass (Safety Core SAF-R005 does the rest).
    `dev_experimental=True` marks sample content as usable for LOCAL demos only."""
    if dev_experimental and os.environ.get("VITAFORGE_ENV", "").lower() == "production" and not ai_curated_demo_acknowledged():
        raise ProductionCatalogError("dev_experimental is forbidden when VITAFORGE_ENV=production")
    loads = tuple(RegionLoad(g, r.region_loads.get(g, "high")) for g in REGIONS)      # unknown region => assume highest loading
    ok_tags = (r.safety_tags_status == "reviewed" and r.expert_review == "approved") or (dev_experimental and r.safety_tags_status == "unreviewed_estimate")
    # a record that merely CLAIMS 'published' is not trusted: it must also have no publication blockers
    published = (r.publication_status == "published" and not publication_blockers(r)) or (dev_experimental and r.publication_status in ("experimental", "draft"))
    status = "published" if published else ("pending_review" if r.publication_status == "published" else r.publication_status)   # a blocked claim is downgraded
    return ExerciseCandidate(code=r.id, review_status=status,
                             safety_tags_complete=ok_tags, movement_pattern=r.movement_pattern, region_loads=loads,
                             contraindications=r.contraindications, cautions=r.cautions, difficulty=r.difficulty, equipment=r.equipment)


def to_catalog_entry(r: ExerciseRecord, dev_experimental: bool = False) -> CatalogExercise:
    return CatalogExercise(to_candidate(r, dev_experimental), r.role, (r.primary_muscles or ("other",))[0], r.push_pull,
                           supports_regions=r.supports_regions, environments=r.environments)


def relations(records) -> dict:
    out = {}
    for r in records:
        rel = [(a, "alternative") for a in r.alternatives] + [(g, "regression") for g in r.regressions]
        if rel:
            out[r.id] = rel
    return out


def publishable(records):
    return [r for r in records if not publication_blockers(r)]


def assert_production_catalog(records) -> None:
    """Startup guard (DOC-10): sample/unreviewed content must never be loaded in production."""
    bad = [r.id for r in records if r.is_sample or r.publication_status != "published" or publication_blockers(r)]
    if bad:
        raise ProductionCatalogError(f"{len(bad)} records are not publishable, e.g. {bad[:3]}")

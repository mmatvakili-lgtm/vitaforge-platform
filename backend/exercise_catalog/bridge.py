"""ExerciseRecord -> Safety Core candidate / Workout Engine catalog entry. Production never lifts review gates."""
from __future__ import annotations

from safety_core.models import REGIONS, ExerciseCandidate, RegionLoad
from workout_engine.models import CatalogExercise

from .schema import ExerciseRecord, publication_blockers


def to_candidate(r: ExerciseRecord, dev_experimental: bool = False) -> ExerciseCandidate:
    """In production only `published` + reviewed tags pass (Safety Core SAF-R005 does the rest).
    `dev_experimental=True` marks sample content as usable for LOCAL demos only."""
    loads = tuple(RegionLoad(g, r.region_loads.get(g, "high")) for g in REGIONS)      # unknown region => assume highest loading
    ok_tags = r.safety_tags_status == "reviewed" or (dev_experimental and r.safety_tags_status == "unreviewed_estimate")
    published = r.publication_status == "published" or (dev_experimental and r.publication_status in ("experimental", "draft"))
    return ExerciseCandidate(code=r.id, review_status="published" if published else r.publication_status,
                             safety_tags_complete=ok_tags, movement_pattern=r.movement_pattern, region_loads=loads,
                             contraindications=r.contraindications, cautions=r.cautions, difficulty=r.difficulty, equipment=r.equipment)


def to_catalog_entry(r: ExerciseRecord, dev_experimental: bool = False) -> CatalogExercise:
    return CatalogExercise(to_candidate(r, dev_experimental), r.role, (r.primary_muscles or ("other",))[0], r.push_pull,
                           supports_regions=r.supports_regions)


def relations(records) -> dict:
    out = {}
    for r in records:
        rel = [(a, "alternative") for a in r.alternatives] + [(g, "regression") for g in r.regressions]
        if rel:
            out[r.id] = rel
    return out


def publishable(records):
    return [r for r in records if not publication_blockers(r)]


class ProductionCatalogError(Exception):
    pass


def assert_production_catalog(records) -> None:
    """Startup guard (DOC-10): sample/unreviewed content must never be loaded in production."""
    bad = [r.id for r in records if r.is_sample or r.publication_status != "published" or publication_blockers(r)]
    if bad:
        raise ProductionCatalogError(f"{len(bad)} records are not publishable, e.g. {bad[:3]}")

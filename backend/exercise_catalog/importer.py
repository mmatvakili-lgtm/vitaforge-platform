"""Import pipeline: external rows -> ExerciseRecord(draft/pending_review), with a per-row report.
Imported rows NEVER arrive published, with safety tags missing and no expert approval."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping

from .schema import ExerciseRecord, SourceRef, validate_record
from .sources import SOURCES

LEVEL_MAP = {"beginner": "beginner", "intermediate": "intermediate", "expert": "advanced", "advanced": "advanced"}
CATEGORY_MAP = {"strength": "strength", "stretching": "stretching", "cardio": "cardio", "plyometrics": "plyometric",
                "powerlifting": "strength", "olympic weightlifting": "strength", "strongman": "strength"}
EQUIP_MAP = {"body only": "bodyweight", "barbell": "barbell", "dumbbell": "dumbbell", "machine": "machine", "cable": "cable",
             "kettlebells": "kettlebell", "bands": "band", "e-z curl bar": "barbell", "medicine ball": "other", "exercise ball": "other",
             "foam roll": "other", "other": "other"}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


@dataclass
class ImportReport:
    accepted: List[ExerciseRecord] = field(default_factory=list)
    rejected: List[Dict] = field(default_factory=list)
    duplicates: List[str] = field(default_factory=list)


def import_free_exercise_db(rows: Iterable[Mapping], existing_ids=()) -> ImportReport:
    """Maps the yuhonas/free-exercise-db JSON schema. Source license is unverified => imported rows are draft + pending."""
    rep, seen = ImportReport(), set(existing_ids)
    for row in rows:
        if not isinstance(row, Mapping):
            rep.rejected.append({"id": "?", "issues": ["row is not an object"]}); continue
        try:
            rid = "fedb_" + slug(str(row.get("id") or row["name"]))
            if rid in seen:
                rep.duplicates.append(rid); continue
            equip = row.get("equipment")
            rec = ExerciseRecord(
                id=rid, name_en=str(row["name"]).strip(),
                primary_muscles=tuple(row.get("primaryMuscles") or ()), secondary_muscles=tuple(row.get("secondaryMuscles") or ()),
                exercise_type=CATEGORY_MAP.get(str(row.get("category", "")).lower(), "strength"),
                equipment=(EQUIP_MAP.get(str(equip).lower(), "other"),) if equip else (),
                difficulty=LEVEL_MAP.get(str(row.get("level", "")).lower(), "beginner"),
                instructions=tuple(row.get("instructions") or ()), publication_status="pending_review",
                sources=(SourceRef("free_exercise_db", str(row.get("id", "")), None),),
                safety_tags_status="missing", expert_review="pending", is_sample=False, movement_pattern="other")
            issues = validate_record(rec)
            if issues:
                rep.rejected.append({"id": rid, "issues": issues}); continue
            rep.accepted.append(rec); seen.add(rid)
        except (KeyError, TypeError, ValueError) as e:
            rep.rejected.append({"id": str(row.get("id", "?")) if isinstance(row, Mapping) else "?", "issues": [f"bad row: {e!r}"]})
    return rep


def load_json_rows(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("expected a JSON list")
    return data

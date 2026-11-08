"""Loads the project-authored starter set. All rows are experimental/sample/pending expert review."""
from __future__ import annotations

import json
import pathlib
from datetime import date

from .schema import ExerciseRecord, SourceRef

DATA = pathlib.Path(__file__).parent / "data" / "starter_exercises.json"


def _rec(d: dict) -> ExerciseRecord:
    d = dict(d)
    d["sources"] = tuple(SourceRef(**s) for s in d.get("sources", []))
    for k in ("aliases", "primary_muscles", "secondary_muscles", "equipment", "instructions", "common_mistakes", "alternatives",
              "regressions", "supports_regions"):
        d[k] = tuple(d.get(k, ()))
    d["contraindications"] = tuple(tuple(x) for x in d.get("contraindications", ()))
    d["cautions"] = tuple(tuple(x) for x in d.get("cautions", ()))
    lr = d.get("last_reviewed")
    d["last_reviewed"] = date.fromisoformat(lr) if lr else None
    return ExerciseRecord(**d)


def load_starter(path=DATA):
    return [_rec(x) for x in json.loads(pathlib.Path(path).read_text(encoding="utf-8"))]

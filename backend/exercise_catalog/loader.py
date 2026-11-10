"""Loads the project-authored starter set. All rows are experimental/sample/pending expert review."""
from __future__ import annotations

import json
import pathlib
from datetime import date

from .schema import ExerciseRecord, MediaRef, SourceRef, validate_record

DATA = pathlib.Path(__file__).parent / "data" / "starter_exercises.json"


def _rec(d: dict) -> ExerciseRecord:
    d = dict(d)
    d["sources"] = tuple(SourceRef(**s) for s in d.get("sources", []))
    for k in ("aliases", "primary_muscles", "secondary_muscles", "equipment", "instructions", "common_mistakes", "alternatives",
              "regressions", "supports_regions", "review_notes", "limitations"):
        d[k] = tuple(d.get(k, ()))
    d["media"] = tuple(MediaRef(**m) for m in d.get("media", ()))
    for k in ("progressions", "environments", "safety_cautions"):
        d[k] = tuple(d.get(k, ()))
    d["contraindications"] = tuple(tuple(x) for x in d.get("contraindications", ()))
    d["cautions"] = tuple(tuple(x) for x in d.get("cautions", ()))
    lr = d.get("last_reviewed")
    d["last_reviewed"] = date.fromisoformat(lr) if lr else None
    return ExerciseRecord(**d)


def load_batches(files):
    rows = [_rec(x) for f in files for x in json.loads(pathlib.Path(f).read_text(encoding="utf-8"))]
    bad = {r.id: validate_record(r) for r in rows if validate_record(r)}
    if bad:
        raise ValueError(f"invalid exercise records: {bad}")            # includes 'published but blocked'
    ids = [r.id for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"duplicate exercise ids across batches: {dup}")
    return rows


def load_starter(path=DATA):
    """Loads every project-authored batch in data/ (sorted by file name) when called with the default; or one given file."""
    p = pathlib.Path(path)
    return load_batches(sorted(p.parent.glob("*.json")) if p == DATA else [p])

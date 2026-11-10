#!/usr/bin/env python3
"""Summarise what blocks each staged exercise from publication and export a reviewer worksheet (CSV). Nothing is approved here."""
import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from exercise_catalog import publication_blockers  # noqa: E402
from exercise_catalog.loader import _rec  # noqa: E402

SRC = ROOT / "backend/exercise_catalog/data/staging/free_exercise_db.json"
OUT = ROOT / "backend/exercise_catalog/data/staging/review_queue.csv"


def main():
    rows = [_rec(x) for x in json.loads(SRC.read_text(encoding="utf-8"))]
    hist = collections.Counter()
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name_en", "equipment", "primary_muscles", "n_steps", "blockers", "reviewer", "decision", "notes"])
        for r in rows:
            b = publication_blockers(r)
            hist.update(b)
            w.writerow([r.id, r.name_en, ";".join(r.equipment), ";".join(r.primary_muscles), len(r.instructions or ()), "|".join(b), "", "", ""])
    print(f"{len(rows)} records; blocker histogram:")
    for k, v in hist.most_common():
        print(f"  {v:5d}  {k}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""python3 tools/equipment_triage.py [exercises.json]  -> backend/exercise_catalog/data/staging/equipment_triage.csv (proposal; vocabulary unchanged)."""
import collections, csv, json, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from exercise_catalog.equipment_triage import triage_all  # noqa: E402
URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
raw = Path(sys.argv[1]).read_bytes() if len(sys.argv) > 1 else urllib.request.urlopen(URL, timeout=60).read()
out = triage_all(json.loads(raw.decode("utf-8")))
p = ROOT / "backend/exercise_catalog/data/staging/equipment_triage.csv"
with p.open("w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["id", "name", "source_equipment", "category", "class", "target", "rule", "reason"])
    for t in sorted(out, key=lambda t: (t.klass, t.target or "", t.id)): w.writerow([t.id, t.name, t.source_equipment, t.category, t.klass, t.target or "", t.rule, t.reason])
print(len(out), dict(collections.Counter(t.klass for t in out)))
for k, v in sorted(collections.Counter((t.target) for t in out if t.klass == "new_category").items(), key=lambda x: -x[1]): print(f"  new_category {v:3d} {k}")

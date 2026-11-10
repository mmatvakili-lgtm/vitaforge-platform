#!/usr/bin/env python3
"""Ingest a USDA FoodData Central JSON download (Foundation or SR Legacy) into STAGING (pending_review, licence unverified).

Get the JSON yourself from https://fdc.nal.usda.gov/download-datasets (the build sandbox cannot reach it), then:
    python3 tools/ingest_usda_fdc.py path/to/FoodData_Central_foundation_food_json_*.json
Output: backend/nutrition_engine/data/staging/usda_fdc.json (+ .manifest.json with sha256, counts, nutrient mismatches).
"""
import dataclasses
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from nutrition_engine.fdc_import import import_fdc  # noqa: E402

OUT = ROOT / "backend/nutrition_engine/data/staging/usda_fdc.json"


def main(argv):
    if len(argv) != 2:
        sys.exit(__doc__)
    raw = Path(argv[1]).read_bytes()
    rep = import_fdc(json.loads(raw.decode("utf-8")), date.today().isoformat())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps([dataclasses.asdict(r) for r in rep.accepted], ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    OUT.with_suffix(".manifest.json").write_text(json.dumps({
        "source": "USDA FoodData Central", "input_file": Path(argv[1]).name, "sha256": hashlib.sha256(raw).hexdigest(), "retrieved": date.today().isoformat(),
        "accepted": len(rep.accepted), "rejected": rep.rejected[:50], "rejected_count": len(rep.rejected), "nutrient_mismatches": rep.nutrient_mismatches, "duplicates": rep.duplicates[:50], "duplicate_count": len(rep.duplicates), "energy_warnings": rep.energy_warnings[:50], "energy_warning_count": len(rep.energy_warnings),
        "licence": "declared public domain / CC0 by FDC; NOT verified by the pipeline (license_verified=false on every record)", "status": "staging only"},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"accepted={len(rep.accepted)} rejected={len(rep.rejected)} mismatches={rep.nutrient_mismatches}")


if __name__ == "__main__":
    main(sys.argv)

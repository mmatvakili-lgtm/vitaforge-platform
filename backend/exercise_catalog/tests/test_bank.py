"""Quality gates for the AI-curated exercise bank (data/bank_*.json is generated from exercise_catalog/bank/*.py)."""
import json
import pathlib

import pytest

from exercise_catalog import load_starter
from exercise_catalog.bank import ALL_BATCHES
from exercise_catalog.schema import validate_record
from safety_core.models import REGIONS

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
ROWS = {r.id: r for r in load_starter()}
BANK = {r["id"]: r for rows in ALL_BATCHES.values() for r in rows}


def test_generated_files_match_the_python_sources():
    for name, rows in ALL_BATCHES.items():
        on_disk = json.loads((DATA / f"bank_{name}.json").read_text(encoding="utf-8"))
        assert on_disk == json.loads(json.dumps(rows, ensure_ascii=False)), f"bank_{name}.json is stale: run `python -m exercise_catalog.bank`"


def test_all_bank_records_are_valid_and_honestly_labelled():
    assert len(BANK) == sum(len(v) for v in ALL_BATCHES.values())            # no duplicate ids inside the bank
    for i in BANK:
        r = ROWS[i]
        assert validate_record(r) == [], i
        assert r.publication_status == "experimental" and r.expert_review == "pending" and r.safety_tags_status == "unreviewed_estimate"
        assert r.evidence_level == "none" and r.is_sample and r.license_status == "project_authored" and r.review_notes
        assert set(r.region_loads) == set(REGIONS)


@pytest.mark.parametrize("i", sorted(BANK))
def test_each_record_is_complete(i):
    r = ROWS[i]
    assert len(r.instructions) >= 3 and len(r.common_mistakes) >= 2, i
    assert r.name_fa and any("؀" <= c <= "ۿ" for c in r.name_fa), i
    assert all(any("؀" <= c <= "ۿ" for c in s) for s in r.instructions), f"{i}: instructions must be Persian"
    assert r.primary_muscles and r.environments, i
    assert r.role in ("main", "accessory") and (r.push_pull in (None, "push", "pull"))


def test_references_exist_and_difficulty_is_coherent():
    for i in BANK:
        r = ROWS[i]
        for k in r.alternatives + r.regressions + r.progressions:
            assert k in ROWS, f"{i} -> unknown {k}"
        assert i not in r.alternatives + r.regressions + r.progressions
        for k in r.regressions:
            assert ORDER[ROWS[k].difficulty] <= ORDER[r.difficulty], f"{i}: regression {k} is harder"
        for k in r.progressions:
            assert ORDER[ROWS[k].difficulty] >= ORDER[r.difficulty], f"{i}: progression {k} is easier"
        fam = lambda p: {"squat": "legs", "lunge": "legs", "core": "trunk", "rotation": "trunk", "carry": "trunk"}.get(p, p)
        for k in r.alternatives:
            assert fam(ROWS[k].movement_pattern) == fam(r.movement_pattern) or "other" in (r.movement_pattern, ROWS[k].movement_pattern), f"{i}: alternative {k} is another pattern family"

def test_loading_scale_is_consistent_with_load_level():
    heavy = [i for i in BANK if ROWS[i].difficulty == "advanced" and "barbell" in ROWS[i].equipment and ROWS[i].movement_pattern in ("squat", "hinge")]
    assert heavy
    for i in heavy:
        assert max(ROWS[i].region_loads[x] == "high" for x in ("lower_back", "hip", "knee")) or ROWS[i].region_loads["lower_back"] in ("moderate", "high"), i
    for i in BANK:
        if ROWS[i].exercise_type == "plyometric":
            assert ROWS[i].cautions, f"{i}: plyometrics need an impact caution"


def test_catalogue_coverage_floors():
    pats = {}
    for r in ROWS.values():
        pats[r.movement_pattern] = pats.get(r.movement_pattern, 0) + 1
    assert len(ROWS) >= 180
    types = {r.exercise_type for r in ROWS.values()}
    assert {"strength", "mobility", "stability", "cardio", "plyometric", "stretching"} <= types
    for p, n in {"squat": 18, "lunge": 12, "hinge": 18, "push_horizontal": 12, "push_vertical": 8, "pull_horizontal": 12, "pull_vertical": 8, "core": 12, "rotation": 3, "carry": 3}.items():
        assert pats.get(p, 0) >= n, (p, pats)

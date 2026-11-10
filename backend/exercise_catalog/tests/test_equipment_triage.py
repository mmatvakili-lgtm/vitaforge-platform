import csv
import json
import pathlib

from exercise_catalog.equipment_triage import CLASSES, triage_row
from exercise_catalog.schema import EQUIPMENT

D = pathlib.Path(__file__).resolve().parents[1] / "data" / "staging"


def test_vocabulary_was_not_expanded_by_triage():
    assert EQUIPMENT == ("dumbbell", "barbell", "bench", "box", "band", "machine", "kettlebell", "pull_up_bar", "cable")


def test_committed_triage_covers_all_out_of_vocabulary_records():
    rows = list(csv.DictReader((D / "equipment_triage.csv").open(encoding="utf-8")))
    staged = json.loads((D / "free_exercise_db.json").read_text(encoding="utf-8"))
    outside = [r for r in staged if any(e not in EQUIPMENT and e != "bodyweight" for e in r["equipment"])]
    assert len(rows) == len(outside) == 162
    assert {r["class"] for r in rows} <= set(CLASSES)
    assert all(r["reason"] and r["rule"] for r in rows)
    assert all(r["target"] in EQUIPMENT for r in rows if r["class"] == "equivalent")


def test_rules_examples():
    t = lambda n, e="other", c="strength": triage_row({"id": n, "name": n, "equipment": e, "category": c})
    assert (t("Seated Band Hamstring Curl").klass, t("Seated Band Hamstring Curl").target) == ("equivalent", "band")
    assert t("Muscle Up").target == "pull_up_bar"
    assert t("Weighted Pull Ups").klass == "ambiguous"
    assert t("Quad Stretch", c="stretching").klass == "unusable"
    assert t("Anything", "medicine ball").target == "medicine_ball"
    assert t("Mystery Move").klass == "ambiguous"

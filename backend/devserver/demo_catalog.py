"""DEMO exercises for local development ONLY. Not clinical content; not reviewed (EXP-011/013)."""
from safety_core.models import REGIONS, ExerciseCandidate, RegionLoad
from workout_engine.models import CatalogExercise

_P = [("squat", "main", "quads", {"knee": "high"}), ("hinge", "main", "glutes", {"lower_back": "high"}),
      ("push_horizontal", "main", "chest", {"shoulder": "high"}), ("pull_horizontal", "main", "back", {"shoulder": "low"}),
      ("push_vertical", "accessory", "delts", {"shoulder": "high"}), ("pull_vertical", "accessory", "back", {"shoulder": "low"}),
      ("lunge", "accessory", "quads", {"knee": "high"}), ("core", "accessory", "abs", {})]


def demo_catalog():
    out = {}
    for p, role, muscle, loads in _P:
        for s in ("a", "b"):
            base = {r: "none" for r in REGIONS}; base.update(loads)
            cand = ExerciseCandidate(f"demo_{p}_{s}", "published", True, p, tuple(RegionLoad(r, l) for r, l in base.items()))
            out[cand.code] = CatalogExercise(cand, role, muscle)
    return out

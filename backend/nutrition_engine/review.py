"""Food review workflow helpers (pure). A human reviewer decides; this module only states what MUST be true before 'reviewed' is allowed.
Nothing here approves anything by itself, and a missing fact is always a blocker, never assumed."""
from __future__ import annotations

import dataclasses
from typing import List

from .food import FoodRecord, validate_food


def approval_blockers(f: FoodRecord) -> List[str]:
    out: List[str] = []
    if f.status == "retired":
        out.append("retired")
    if f.is_test_fixture:
        out.append("test_fixture")
    if f.source is None:
        out.append("no_source")
    elif not f.source.license_verified:
        out.append("license_not_verified")
    if not f.allergens_known:
        out.append("allergens_unknown")
    if "kcal" not in f.per_100g:
        out.append("no_energy_value")
    out += [f"invalid:{p}" for p in validate_food(f)]
    return out


def decide(f: FoodRecord, decision: str, notes: str) -> FoodRecord:
    """Returns the updated record or raises ValueError(reason). Reject/retire need a written reason."""
    if decision == "approve":
        b = approval_blockers(f)
        if b:
            raise ValueError(",".join(b))
        return dataclasses.replace(f, status="reviewed")
    if decision in ("reject", "retire"):
        if len(notes.strip()) < 5:
            raise ValueError("notes_required")
        return dataclasses.replace(f, status="retired")
    raise ValueError("decision")

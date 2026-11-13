"""Loads imported (pending_review) foods into a store without ever overwriting an existing record, so a reviewed food is never reset by a re-import."""
from __future__ import annotations

from typing import Dict, Iterable


def load_foods(store_foods: Dict[str, object], records: Iterable) -> Dict[str, int]:
    added = skipped = 0
    for r in records:
        if r.status != "pending_review" or r.id in store_foods:
            skipped += 1
            continue
        store_foods[r.id] = r
        added += 1
    return {"added": added, "skipped_existing_or_not_pending": skipped}

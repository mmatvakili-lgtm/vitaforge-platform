"""Demo/test food + recipe content (LOCAL DEMO / AI-curated demo only; never loaded in the production posture).

Composition values are unmodified USDA FoodData Central Foundation Foods rows (declared public domain/CC0 by FDC; not re-verified here),
imported through `fdc_import` so every nutrient is matched by number+unit+name. Persian names, allergens, diet tags and the recipes are
AI-curated and NOT expert reviewed: everything stays `pending_review` and is labelled as unreviewed in the API/UI.
Allergen tagging is deliberately conservative (processed foods carry every plausible allergen); "halal" for meat assumes a halal-slaughtered
supply (Iran market) and is noted on the record; pork/alcohol are not present.
"""
from __future__ import annotations

import dataclasses
import functools
import json
import pathlib
from typing import Dict, Tuple

from .fdc_import import import_fdc
from .food import FoodRecord, validate_food
from .recipes import Recipe, validate_recipe

_DIR = pathlib.Path(__file__).parent / "data"
RETRIEVED = "2026-11-17"


@functools.lru_cache(maxsize=1)
def demo_content() -> Tuple[Dict[str, FoodRecord], Tuple[Recipe, ...]]:
    cur = json.loads((_DIR / "demo_curation.json").read_text(encoding="utf-8"))
    rep = import_fdc(json.loads((_DIR / "demo_foods_fdc.json").read_text(encoding="utf-8")), RETRIEVED, dataset="usda_fdc_foundation", derive_missing_energy=True)
    foods: Dict[str, FoodRecord] = {}
    for f in rep.accepted:
        c = cur.get(f.id)
        if not c:
            continue
        notes = tuple(n for n in f.notes if n not in ("allergen status unknown", "no diet tags asserted", "no Persian name")) + (
            "AI-curated allergens/diet tags/Persian name; not expert reviewed", "values are for the raw/dry state as in the FDC record")
        if "halal" in c["diet_tags"] and f.category and any(k in f.category for k in ("Poultry", "Beef", "Finfish")):
            notes += ("halal tag assumes a halal-slaughtered supply (Iran market)",)
        g = dataclasses.replace(f, name_fa=c["name_fa"], allergens=tuple(c["allergens"]), diet_tags=tuple(c["diet_tags"]),
                                allergens_known=True, notes=notes)
        assert not validate_food(g), (g.id, validate_food(g))
        foods[g.id] = g
    recipes = []
    for r in json.loads((_DIR / "demo_recipes.json").read_text(encoding="utf-8")):
        rec = Recipe(id=r["id"], name_en=r["name_en"], name_fa=r["name_fa"], slots=tuple(r["slots"]),
                     ingredients=tuple((i, float(g)) for i, g in r["ingredients"]), servings=r["servings"], cook_minutes=r["cook_minutes"],
                     steps=tuple(r["steps"]), status="pending_review")
        assert not validate_recipe(rec, foods), (rec.id, validate_recipe(rec, foods))
        recipes.append(rec)
    return foods, tuple(recipes)

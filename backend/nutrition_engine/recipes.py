"""Recipes reference food records by id; their nutrition is DERIVED from the foods (never typed in)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple

from .food import FoodRecord, NUTRIENTS

SLOTS = ("breakfast", "lunch", "dinner", "snack")
RECIPE_STATUSES = ("draft", "pending_review", "reviewed", "retired")


@dataclass(frozen=True)
class Recipe:
    id: str
    name_en: str
    name_fa: Optional[str] = None
    slots: Tuple[str, ...] = ("lunch", "dinner")
    ingredients: Tuple[Tuple[str, float], ...] = ()      # (food_id, grams for the whole recipe)
    servings: int = 1
    cook_minutes: int = 30
    steps: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()                           # diet tags the recipe satisfies (must be implied by ingredients; checked)
    status: str = "pending_review"
    is_test_fixture: bool = False


def validate_recipe(r: Recipe, foods: Mapping[str, FoodRecord]) -> list:
    p = []
    if not r.ingredients or r.servings < 1 or r.cook_minutes < 0: p.append("shape")
    if r.status not in RECIPE_STATUSES: p.append("status")
    if any(s not in SLOTS for s in r.slots): p.append("slot")
    for fid, g in r.ingredients:
        if fid not in foods: p.append(f"unknown food {fid}")
        if g <= 0: p.append("grams")
    if r.status == "reviewed" and r.is_test_fixture: p.append("fixture cannot be reviewed")
    return p


def recipe_allergens(r: Recipe, foods: Mapping[str, FoodRecord]) -> Tuple[set, bool]:
    """(allergens present in any ingredient, all_known). Unknown allergen status of ANY ingredient makes the whole recipe unknown."""
    al, known = set(), True
    for fid, _ in r.ingredients:
        f = foods[fid]
        al |= set(f.allergens)
        known &= f.allergens_known
    return al, known


def recipe_diet_tags(r: Recipe, foods: Mapping[str, FoodRecord]) -> set:
    """A recipe satisfies a diet tag only if EVERY ingredient carries it (conservative; declared recipe tags are not trusted on their own)."""
    sets = [set(foods[fid].diet_tags) for fid, _ in r.ingredients]
    return set.intersection(*sets) if sets else set()


def nutrition_per_serving(r: Recipe, foods: Mapping[str, FoodRecord]) -> Tuple[Dict[str, float], Tuple[str, ...]]:
    """Returns (nutrients per serving, nutrients missing for at least one ingredient). Missing values are not summed as zero silently."""
    tot: Dict[str, float] = {}
    missing = set()
    for fid, g in r.ingredients:
        per = foods[fid].per_100g
        for k in NUTRIENTS:
            if k in per:
                tot[k] = tot.get(k, 0.0) + per[k] * g / 100.0
            else:
                missing.add(k)
    return {k: v / r.servings for k, v in tot.items()}, tuple(sorted(missing))

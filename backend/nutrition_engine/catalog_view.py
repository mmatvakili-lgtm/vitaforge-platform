"""Read models for browsing foods and recipes. Visibility mirrors the exercise gate: only `reviewed` data is served, plus `pending_review` data ONLY when the
rule set explicitly allows unreviewed content (development); retired data is never served. Everything unreviewed is labelled. Nothing here invents values:
nutrients absent in the source stay absent (missing != 0) and allergen status stays `allergens_known=False` until known."""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from .food import FoodRecord
from .recipes import Recipe, nutrition_per_serving, recipe_allergens, recipe_diet_tags

SUMMARY_NUTRIENTS = ("kcal", "protein_g", "fat_g", "carbs_g")


def visible(status: str, allow_unreviewed: bool) -> bool:
    return status == "reviewed" or (allow_unreviewed and status == "pending_review")


def food_label(f: FoodRecord) -> str:
    return "reviewed" if f.status == "reviewed" and not f.is_test_fixture else "unreviewed"


def recipe_label(r: Recipe, foods: Mapping[str, FoodRecord]) -> str:
    """A reviewed recipe is only as trustworthy as its ingredients."""
    ok = r.status == "reviewed" and not r.is_test_fixture and all(i in foods and food_label(foods[i]) == "reviewed" for i, _ in r.ingredients)
    return "reviewed" if ok else "unreviewed"


def _text(f: FoodRecord) -> str:
    return f"{f.id} {f.name_en} {f.name_fa or ''} {f.category}".lower()


def food_summary(f: FoodRecord) -> dict:
    out = {"id": f.id, "name_en": f.name_en, "category": f.category, "allergens": list(f.allergens), "allergens_known": f.allergens_known,
           "diet_tags": list(f.diet_tags), "review_status": food_label(f), "per_100g": {k: f.per_100g[k] for k in SUMMARY_NUTRIENTS if k in f.per_100g}}
    if f.name_fa:
        out["name_fa"] = f.name_fa
    return out


def food_detail(f: FoodRecord) -> dict:
    out = food_summary(f)
    out.update({"per_100g": dict(f.per_100g), "serving_g": dict(f.serving_g), "basis": f.basis, "notes": list(f.notes),
                "nutrient_refs": {k: dict(v) for k, v in f.nutrient_refs.items()}})
    if f.source:
        out["source"] = {"dataset": f.source.dataset, "record_id": f.source.record_id, "license": f.source.license, "license_verified": f.source.license_verified}
    return out


def search_foods(foods: Mapping[str, FoodRecord], allow_unreviewed: bool, q: str = "", category: str = "", diet: str = "",
                 avoid_allergens: Sequence[str] = ()) -> List[FoodRecord]:
    needle, avoid = q.strip().lower(), set(avoid_allergens)
    rows = []
    for f in foods.values():
        if not visible(f.status, allow_unreviewed):
            continue
        if needle and needle not in _text(f) or category and f.category != category or diet and diet not in f.diet_tags:
            continue
        if avoid and (avoid & set(f.allergens) or not f.allergens_known):           # unknown allergen status is treated as unsafe, never as "none"
            continue
        rows.append(f)
    return sorted(rows, key=lambda f: (f.name_en.lower(), f.id))


def recipe_summary(r: Recipe, foods: Mapping[str, FoodRecord]) -> dict:
    per, missing = nutrition_per_serving(r, foods)
    al, known = recipe_allergens(r, foods)
    out = {"id": r.id, "name_en": r.name_en, "slots": list(r.slots), "cook_minutes": r.cook_minutes, "servings": r.servings,
           "per_serving": {k: round(per[k], 1) for k in SUMMARY_NUTRIENTS if k in per}, "missing_nutrients": [m for m in missing if m in SUMMARY_NUTRIENTS],
           "allergens": sorted(al), "allergens_known": known, "diet_tags": sorted(recipe_diet_tags(r, foods)), "review_status": recipe_label(r, foods)}
    if r.name_fa:
        out["name_fa"] = r.name_fa
    return out


def recipe_detail(r: Recipe, foods: Mapping[str, FoodRecord]) -> dict:
    out = recipe_summary(r, foods)
    per, missing = nutrition_per_serving(r, foods)
    out["per_serving"] = {k: round(v, 1) for k, v in per.items()}
    out["missing_nutrients"] = list(missing)
    out["steps"] = list(r.steps)
    out["ingredients"] = [{"food_id": i, "name_en": foods[i].name_en, **({"name_fa": foods[i].name_fa} if foods[i].name_fa else {}), "grams": g,
                          "allergens": list(foods[i].allergens), "allergens_known": foods[i].allergens_known} for i, g in r.ingredients]
    return out


def recipe_is_servable(r: Recipe, foods: Mapping[str, FoodRecord], allow_unreviewed: bool) -> bool:
    return visible(r.status, allow_unreviewed) and all(i in foods and visible(foods[i].status, allow_unreviewed) for i, _ in r.ingredients)


def search_recipes(recipes: Iterable[Recipe], foods: Mapping[str, FoodRecord], allow_unreviewed: bool, q: str = "", slot: str = "", diet: str = "",
                   max_minutes: Optional[int] = None, avoid_allergens: Sequence[str] = ()) -> List[Recipe]:
    needle, avoid = q.strip().lower(), set(avoid_allergens)
    rows = []
    for r in recipes:
        if not recipe_is_servable(r, foods, allow_unreviewed):
            continue
        if needle and needle not in f"{r.id} {r.name_en} {r.name_fa or ''}".lower() or slot and slot not in r.slots or max_minutes is not None and r.cook_minutes > max_minutes:
            continue
        if diet and diet not in recipe_diet_tags(r, foods):
            continue
        al, known = recipe_allergens(r, foods)
        if avoid and (avoid & al or not known):
            continue
        rows.append(r)
    return sorted(rows, key=lambda r: (r.name_en.lower(), r.id))

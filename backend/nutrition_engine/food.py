"""Food composition model. Composition is SEPARATE from market prices (prices.py). Values are per 100 g edible portion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

NUTRIENTS = ("kcal", "protein_g", "fat_g", "carbs_g", "fiber_g", "sugar_g", "sodium_mg", "calcium_mg", "iron_mg", "potassium_mg", "vitamin_c_mg")
FOOD_STATUSES = ("pending_review", "reviewed", "retired")
ALLERGENS = ("milk", "egg", "fish", "shellfish", "tree_nut", "peanut", "wheat", "soy", "sesame")
DIET_TAGS = ("vegetarian", "vegan", "halal", "gluten_free", "lactose_free")


@dataclass(frozen=True)
class FoodSource:
    dataset: str                         # e.g. usda_fdc_foundation
    record_id: str                       # e.g. FDC id
    license: str = "unknown"
    license_verified: bool = False
    published: Optional[str] = None      # publication date of the record in the source
    retrieved: Optional[str] = None


@dataclass(frozen=True)
class FoodRecord:
    id: str
    name_en: str
    name_fa: Optional[str] = None
    category: str = ""
    per_100g: Mapping[str, float] = field(default_factory=dict)          # only nutrients actually present in the source (missing != 0)
    serving_g: Mapping[str, float] = field(default_factory=dict)         # household measure -> grams
    allergens: Tuple[str, ...] = ()
    diet_tags: Tuple[str, ...] = ()
    allergens_known: bool = False        # False => allergen status UNKNOWN; such foods are excluded when the user has any allergy
    source: Optional[FoodSource] = None
    status: str = "pending_review"
    is_test_fixture: bool = False
    notes: Tuple[str, ...] = ()


def validate_food(f: FoodRecord) -> list:
    p = []
    if not f.id or not f.name_en: p.append("id/name_en")
    if f.status not in FOOD_STATUSES: p.append("status")
    if any(k not in NUTRIENTS for k in f.per_100g): p.append("unknown nutrient key")
    if any((not isinstance(v, (int, float))) or v < 0 for v in f.per_100g.values()): p.append("negative/non-numeric nutrient")
    if "kcal" in f.per_100g and f.per_100g["kcal"] > 900: p.append("kcal/100g implausible")
    if any(a not in ALLERGENS for a in f.allergens): p.append("allergen vocabulary")
    if any(t not in DIET_TAGS for t in f.diet_tags): p.append("diet tag vocabulary")
    if any(g <= 0 for g in f.serving_g.values()): p.append("serving grams")
    if f.status == "reviewed" and (f.source is None or not f.source.license_verified or f.is_test_fixture): p.append("reviewed requires verified source licence and a non-fixture")
    return p


def usable_for_planning(f: FoodRecord, allow_unreviewed: bool) -> bool:
    """Planning needs energy+protein+fat+carbs. Unreviewed data is usable only when the caller explicitly allows it (labelled in the output)."""
    core = all(k in f.per_100g for k in ("kcal", "protein_g", "fat_g", "carbs_g"))
    return core and f.status != "retired" and (f.status == "reviewed" or allow_unreviewed)

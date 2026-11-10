"""USDA FoodData Central importer (Foundation / SR Legacy JSON) -> FoodRecord(pending_review).

Licence: FDC states its data are in the public domain (CC0 1.0). That statement was NOT re-verified in the build sandbox (site unreachable),
so records carry license='CC0-1.0 (declared by FDC)' with license_verified=False until a human confirms it. Nothing is ever 'reviewed'.
Nutrient numbers are matched by number AND unit AND an expected name fragment, so a wrong mapping rejects the nutrient instead of
silently mis-assigning it. Allergens/diet tags are NOT in FDC: allergens_known=False, no diet tags are asserted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping

from .food import FoodRecord, FoodSource, validate_food

# key -> (FDC nutrient numbers tried in order, expected unit, expected name fragment)
NUTRIENT_MAP = {
    "kcal": (("208", "957", "958"), "KCAL", "energy"),
    "protein_g": (("203",), "G", "protein"),
    "fat_g": (("204",), "G", "lipid"),
    "carbs_g": (("205",), "G", "carbohydrate"),
    "fiber_g": (("291",), "G", "fiber"),
    "sugar_g": (("269", "269.3"), "G", "sugars"),
    "sodium_mg": (("307",), "MG", "sodium"),
    "calcium_mg": (("301",), "MG", "calcium"),
    "iron_mg": (("303",), "MG", "iron"),
    "potassium_mg": (("306",), "MG", "potassium"),
    "vitamin_c_mg": (("401",), "MG", "vitamin c"),
}
LIST_KEYS = ("FoundationFoods", "SRLegacyFoods")


@dataclass
class FdcReport:
    accepted: List[FoodRecord] = field(default_factory=list)
    rejected: List[Dict] = field(default_factory=list)
    nutrient_mismatches: int = 0


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:60]


def rows_from_json(data) -> list:
    if isinstance(data, list):
        return data
    for k in LIST_KEYS:
        if isinstance(data, Mapping) and isinstance(data.get(k), list):
            return data[k]
    raise ValueError("unrecognised FDC JSON shape (expected a list, FoundationFoods or SRLegacyFoods)")


def import_fdc(data, retrieved: str, dataset: str = "usda_fdc") -> FdcReport:
    rep = FdcReport()
    seen = set()
    for row in rows_from_json(data):
        try:
            fdc_id = str(row["fdcId"])
            name = str(row["description"]).strip()
            per: Dict[str, float] = {}
            for fn in row.get("foodNutrients", ()):
                nut = fn.get("nutrient") or {}
                num, amt = str(nut.get("number", "")), fn.get("amount")
                if amt is None:
                    continue
                for key, (nums, unit, frag) in NUTRIENT_MAP.items():
                    if num in nums and key not in per:
                        if str(nut.get("unitName", "")).upper() == unit and frag in str(nut.get("name", "")).lower():
                            per[key] = float(amt)
                        else:
                            rep.nutrient_mismatches += 1
            servings = {}
            for p in row.get("foodPortions", ()) or ():
                gw = p.get("gramWeight")
                label = (p.get("portionDescription") or p.get("modifier") or "").strip()
                if gw and float(gw) > 0 and label and label.lower() != "undetermined":
                    servings[label] = float(gw)
            fid = f"fdc_{fdc_id}"
            if fid in seen:
                continue
            rec = FoodRecord(
                id=fid, name_en=name, category=((row.get("foodCategory") or {}).get("description") if isinstance(row.get("foodCategory"), Mapping) else str(row.get("foodCategory") or "")),
                per_100g=per, serving_g=servings, allergens_known=False,
                source=FoodSource(dataset, fdc_id, "CC0-1.0 (declared by FDC; not re-verified)", False, str(row.get("publicationDate") or "") or None, retrieved),
                status="pending_review", notes=("allergen status unknown", "no diet tags asserted", "no Persian name"))
            issues = validate_food(rec)
            if issues:
                rep.rejected.append({"id": fid, "issues": issues}); continue
            seen.add(fid); rep.accepted.append(rec)
        except (KeyError, TypeError, ValueError) as e:
            rep.rejected.append({"id": str(row.get("fdcId", "?")) if isinstance(row, Mapping) else "?", "issues": [repr(e)]})
    return rep

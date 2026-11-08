"""Meal & water log + history summary. User-entered values are labelled `user_entered`; no invented nutrition data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app_services.errors import NotFound, ValidationFailed


@dataclass(frozen=True)
class MealEntry:
    id: str
    day: int
    name: str
    kcal: Optional[float]
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    source: str = "user_entered"


class NutritionLog:
    def __init__(self, store, today):
        self.s, self.today = store, today
        self.s.__dict__.setdefault("meals", {})
        self.s.__dict__.setdefault("water", {})

    def add_meal(self, uid, name, kcal=None, protein_g=None, carbs_g=None, fat_g=None, day=None):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            raise ValidationFailed("name")
        for v, hi in ((kcal, 5000), (protein_g, 400), (carbs_g, 1000), (fat_g, 400)):
            if v is not None and (not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= hi):
                raise ValidationFailed("macro")
        if all(v is None for v in (kcal, protein_g, carbs_g, fat_g)):
            raise ValidationFailed("empty")
        e = MealEntry(self.s.new_id("meal"), day if day is not None else self.today(), name.strip(), kcal, protein_g, carbs_g, fat_g)
        self.s.meals.setdefault(uid, []).append(e)
        return e

    def delete_meal(self, uid, mid):
        rows = self.s.meals.get(uid, [])
        for i, e in enumerate(rows):
            if e.id == mid:
                rows.pop(i); return
        raise NotFound()

    def add_water(self, uid, ml, day=None):
        if not isinstance(ml, (int, float)) or isinstance(ml, bool) or not 50 <= ml <= 3000:
            raise ValidationFailed("ml")
        self.s.water.setdefault(uid, []).append({"day": day if day is not None else self.today(), "ml": ml})

    def day_summary(self, uid, day=None, estimate=None):
        day = day if day is not None else self.today()
        meals = [m for m in self.s.meals.get(uid, []) if m.day == day]
        tot = lambda f: round(sum(getattr(m, f) or 0 for m in meals), 1)
        known = {f: sum(1 for m in meals if getattr(m, f) is not None) for f in ("kcal", "protein_g", "carbs_g", "fat_g")}
        out = {"day": day, "meals": len(meals), "kcal": tot("kcal"), "protein_g": tot("protein_g"), "carbs_g": tot("carbs_g"),
               "fat_g": tot("fat_g"), "water_ml": sum(w["ml"] for w in self.s.water.get(uid, []) if w["day"] == day),
               "completeness": {k: f"{v}/{len(meals)}" for k, v in known.items()},
               "note": "user-entered values; incomplete entries are not estimated"}
        if estimate and estimate.tdee:
            out["vs_estimate"] = {"tdee_range": [estimate.tdee[0], estimate.tdee[2]], "uncertainty": estimate.uncertainty}
        return out

    def history(self, uid, from_day, to_day):
        days: Dict[int, int] = {}
        for m in self.s.meals.get(uid, []):
            if from_day <= m.day <= to_day:
                days[m.day] = days.get(m.day, 0) + 1
        return [{"day": d, "meals": n} for d, n in sorted(days.items())]

"""Nutrition engine (DOC-12): estimates with stated uncertainty. NOT medical nutrition therapy.

Formula source: Mifflin MD et al., Am J Clin Nutr 1990;51(2):241-7 (healthy adults) -- see exercise_catalog.sources["mifflin_1990"].
Activity multipliers, macro/water ranges and BMI guards are ENGINEERING DEFAULTS (status=unverified, EXP-006): they are labelled in
every output, and numeric weight-change targets stay disabled until `bounds_reviewed=True` is set from an approved config.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Tuple

from safety_core import SafetyCore
from safety_core.models import SafetyRequest

SEXES = ("male", "female")
ACTIVITY = ("sedentary", "light", "moderate", "active", "very_active")
GOALS = ("maintain", "lose", "gain")
SCREEN_KEYS = ("eating_disorder_risk", "medical_diet_needed", "pregnant_or_lactating")


@dataclass(frozen=True)
class NutritionConfig:
    version: int = 1
    status: str = "unverified"
    bounds_reviewed: bool = False                 # True only from an expert-approved config (EXP-006)
    show_unverified_ranges: bool = True           # False in production until reviewed
    pal: Mapping[str, float] = field(default_factory=lambda: {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9})
    bmr_uncertainty_pct: float = 10.0
    protein_g_per_kg: Tuple[float, float] = (1.2, 2.0)
    fat_pct_energy: Tuple[float, float] = (20.0, 35.0)
    water_ml_per_kg: Tuple[float, float] = (30.0, 35.0)
    bmi_min_for_targets: float = 17.0
    bmi_max_for_targets: float = 45.0
    age_max_for_targets: int = 80


@dataclass(frozen=True)
class NutritionProfile:
    age: Optional[int]
    sex: Optional[str]                  # male | female | None
    height_cm: Optional[float]
    weight_kg: Optional[float]
    activity: Optional[str]
    goal: str = "maintain"
    screening: Mapping[str, Optional[bool]] = field(default_factory=dict)
    allergens: Tuple[str, ...] = ()
    diet_tags: Tuple[str, ...] = ()


@dataclass(frozen=True)
class NutritionResult:
    status: str                         # OK | NEEDS_INFO | BLOCKED | REFER
    reasons: Tuple[str, ...] = ()
    questions: Tuple[str, ...] = ()
    bmr: Optional[Tuple[float, float, float]] = None          # (low, central, high)
    tdee: Optional[Tuple[float, float, float]] = None
    macros: Optional[Dict[str, Tuple[float, float]]] = None   # grams per day (ranges)
    water_ml: Optional[Tuple[float, float]] = None
    goal_adjustment: str = "disabled_pending_expert_review"
    uncertainty: str = "high"
    labels: Tuple[str, ...] = ("estimate", "unverified_parameters", "not_medical_advice")
    safety_decision_id: Optional[str] = None
    method: str = "mifflin_st_jeor_1990 x PAL(config)"


def _bmr(sex: str, w: float, h: float, a: int) -> float:
    return 10 * w + 6.25 * h - 5 * a + (5 if sex == "male" else -161)


def estimate(p: NutritionProfile, gate: SafetyCore, base: SafetyRequest, cfg: NutritionConfig = NutritionConfig()) -> NutritionResult:
    """N0..N3 of DOC-12. Never raises on bad user input; returns NEEDS_INFO/BLOCKED/REFER instead."""
    import dataclasses
    d = gate.evaluate(dataclasses.replace(base, candidates=(), context_type="nutrition"))
    if not d.status.permits_content:
        return NutritionResult("BLOCKED", ("SAFETY:" + d.status.value,) + d.reasons, safety_decision_id=d.decision_id)
    missing = [k for k, v in (("age", p.age), ("height_cm", p.height_cm), ("weight_kg", p.weight_kg), ("activity", p.activity)) if v is None]
    missing += [f"screening:{k}" for k in SCREEN_KEYS if p.screening.get(k) is None]
    if missing:
        return NutritionResult("NEEDS_INFO", ("NUT-MISSING",), tuple(missing), safety_decision_id=d.decision_id)
    if p.activity not in ACTIVITY or p.goal not in GOALS or p.sex not in SEXES + (None,):
        return NutritionResult("NEEDS_INFO", ("NUT-BAD-INPUT",), ("activity/goal/sex",), safety_decision_id=d.decision_id)
    if not (10 <= p.age < 120) or not (100 <= p.height_cm <= 250) or not (25 <= p.weight_kg <= 400):
        return NutritionResult("NEEDS_INFO", ("NUT-IMPLAUSIBLE-INPUT",), ("age/height/weight",), safety_decision_id=d.decision_id)
    if p.screening["eating_disorder_risk"]:                                   # NUT-R02 (DEC-117)
        return NutritionResult("REFER", ("NUT-R02",), safety_decision_id=d.decision_id)
    if p.screening["medical_diet_needed"] or p.screening["pregnant_or_lactating"]:   # NUT-R04 / out of scope
        return NutritionResult("REFER", ("NUT-R04",), safety_decision_id=d.decision_id)
    bmi = p.weight_kg / (p.height_cm / 100) ** 2
    if bmi < cfg.bmi_min_for_targets or bmi > cfg.bmi_max_for_targets or p.age > cfg.age_max_for_targets:
        return NutritionResult("REFER", ("NUT-OUT-OF-RANGE-GUARD",), safety_decision_id=d.decision_id)

    sexes = (p.sex,) if p.sex else SEXES
    vals = [_bmr(s, p.weight_kg, p.height_cm, p.age) for s in sexes]
    central = sum(vals) / len(vals)
    spread = cfg.bmr_uncertainty_pct / 100
    low, high = min(vals) * (1 - spread), max(vals) * (1 + spread)
    pal = cfg.pal[p.activity]
    tdee = (low * pal, central * pal, high * pal)
    reasons = ["NUT-ESTIMATE"]
    macros = water = None
    if cfg.show_unverified_ranges or cfg.bounds_reviewed:
        macros = {"protein_g": (round(cfg.protein_g_per_kg[0] * p.weight_kg), round(cfg.protein_g_per_kg[1] * p.weight_kg)),
                  "fat_g": (round(cfg.fat_pct_energy[0] / 100 * tdee[1] / 9), round(cfg.fat_pct_energy[1] / 100 * tdee[1] / 9))}
        p_kcal = (macros["protein_g"][0] * 4, macros["protein_g"][1] * 4)
        macros["carbs_g"] = (max(0, round((tdee[1] - p_kcal[1] - cfg.fat_pct_energy[1] / 100 * tdee[1]) / 4)),
                             max(0, round((tdee[1] - p_kcal[0] - cfg.fat_pct_energy[0] / 100 * tdee[1]) / 4)))
        water = (round(cfg.water_ml_per_kg[0] * p.weight_kg, -1), round(cfg.water_ml_per_kg[1] * p.weight_kg, -1))
    if p.goal != "maintain" and not cfg.bounds_reviewed:
        reasons.append("NUT-R03:goal-targets-disabled")                       # maintenance estimate only
    adj = "enabled" if cfg.bounds_reviewed else "disabled_pending_expert_review"
    unc = "high" if p.sex is None else "medium"
    return NutritionResult("OK", tuple(reasons), bmr=(round(low), round(central), round(high)),
                           tdee=tuple(round(x) for x in tdee), macros=macros, water_ml=water, goal_adjustment=adj, uncertainty=unc,
                           safety_decision_id=d.decision_id)


# ---------------------------------------------------------------- food filtering (NUT-R01, NUT-R05) for a future FoodDataSource
@dataclass(frozen=True)
class FoodItem:
    id: str
    name: str
    allergens: Tuple[str, ...] = ()
    traces: Tuple[str, ...] = ()
    diet_tags: Tuple[str, ...] = ()            # e.g. vegetarian, halal
    source: Optional[str] = None
    source_date: Optional[str] = None


def filter_foods(foods, allergens=(), diet_required=()) -> Tuple[FoodItem, ...]:
    """Hard filter: allergen or trace match, missing source/date, or unmet diet tag => excluded (never 'softened')."""
    al = {a.lower() for a in allergens}
    need = set(diet_required)
    out = []
    for f in foods:
        if not f.source or not f.source_date:
            continue
        if al & {a.lower() for a in f.allergens} or al & {a.lower() for a in f.traces}:
            continue
        if need and not need <= set(f.diet_tags):
            continue
        out.append(f)
    return tuple(out)

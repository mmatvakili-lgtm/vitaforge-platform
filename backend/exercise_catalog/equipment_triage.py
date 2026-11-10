"""Triage of source equipment values that fall outside the controlled vocabulary. Produces a PROPOSAL only: the vocabulary is never changed here.

Classes: equivalent (maps to an existing vocabulary item), new_category (a genuine implement the vocabulary lacks), ambiguous (needs a human),
unusable (the value carries no usable equipment information or the activity is out of scope for equipment-based planning).
Evidence is the source's own equipment value, category and exercise name; every row records the rule that fired.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional

CLASSES = ("equivalent", "new_category", "ambiguous", "unusable")

# (rule id, regex on lower-cased name, class, target, reason). First match wins; order matters.
RULES = [
    ("R-STRONGMAN", r"atlas stone|axle|car deadlift|circus bell|conan|crucifix|keg load|log lift|power stairs|rickshaw|sandbag|tire flip|yoke|farmer's walk|backward drag|bear crawl sled|forward drag", "new_category", "strongman_implement", "specialised strongman implement; also out of scope for a general-population plan"),
    ("R-SLED", r"\bsled\b|prowler", "new_category", "sled", "sled/prowler"),
    ("R-SUSPENSION", r"suspended|inverted row with straps", "new_category", "suspension_trainer", "suspension straps"),
    ("R-RINGS", r"\bring dips\b", "new_category", "gymnastic_rings", "rings"),
    ("R-DIPSTATION", r"parallel bar|dips - chest|bench dip", "ambiguous", "dip_station_or_bench", "dip on parallel bars (new category) or on a bench (existing 'bench'); the source value does not say"),
    ("R-WEIGHTED-PULL", r"weighted pull", "ambiguous", "pull_up_bar+external_load", "needs a pull-up bar AND an unspecified external load"),
    ("R-BAND-PULL", r"band assisted pull", "ambiguous", "pull_up_bar+band", "needs two existing items; the model stores one item per requirement set only after review"),
    ("R-PULLUP", r"chin|pull-up|muscle up|one handed hang|rocky pull|london bridges|gironda", "equivalent", "pull_up_bar", "hang/pull on a bar"),
    ("R-WEIGHTED-BAND", r"weighted .*band", "ambiguous", "band+external_load", "band plus an unspecified external load"),
    ("R-BAND", r"\bband", "equivalent", "band", "resistance band named in the exercise"),
    ("R-BOX", r"box", "equivalent", "box", "box/platform named in the exercise"),
    ("R-ROPE-CLIMB", r"rope climb", "new_category", "climbing_rope", "climbing rope"),
    ("R-BATTLE-ROPE", r"battling rope", "new_category", "battle_rope", "battle rope"),
    ("R-JUMP-ROPE", r"rope jumping", "new_category", "jump_rope", "jump rope"),
    ("R-PLATE", r"\bplate\b|svend", "new_category", "weight_plate", "weight plate as the load"),
    ("R-ABWHEEL", r"ab roller", "new_category", "ab_wheel", "ab wheel"),
    ("R-TRAPBAR", r"trap bar", "new_category", "trap_bar", "trap/hex bar"),
    ("R-HYPER", r"hyperextension", "new_category", "hyperextension_bench", "back-extension bench"),
    ("R-PLYO-PROPS", r"cone|hurdle", "new_category", "agility_props", "cones/hurdles"),
    ("R-BALANCE", r"balance board", "new_category", "balance_board", "balance board"),
    ("R-WRIST", r"wrist roller", "new_category", "wrist_roller", "wrist roller"),
    ("R-BAG", r"heavy bag", "new_category", "heavy_bag", "heavy bag"),
    ("R-HAMMER", r"sledgehammer", "new_category", "sledgehammer_and_tire", "sledgehammer"),
    ("R-NECK-HARNESS", r"head harness", "new_category", "neck_harness", "neck harness"),
    ("R-CARDIO-ACTIVITY", r"bicycling|skating", "unusable", None, "cardio activity needing a bicycle/skates; not equipment-based strength content"),
    ("R-BENCH", r"bench sprint", "ambiguous", "bench", "sprint over a bench; unclear whether a bench is required"),
]
SOURCE_VALUE_RULES = {
    "medicine ball": ("new_category", "medicine_ball", "R-SRC-MEDBALL", "distinct implement not in the vocabulary"),
    "exercise ball": ("new_category", "stability_ball", "R-SRC-BALL", "distinct implement not in the vocabulary"),
    "foam roll": ("ambiguous", "foam_roller", "R-SRC-FOAM", "implement is clear, but self-myofascial release is mobility content outside the current exercise scope"),
}


@dataclass(frozen=True)
class Triage:
    id: str
    name: str
    source_equipment: Optional[str]
    category: str
    klass: str
    target: Optional[str]
    rule: str
    reason: str


def triage_row(row: Mapping) -> Triage:
    name, src, cat = str(row.get("name", "")), row.get("equipment"), str(row.get("category", ""))
    low = name.lower()
    rid = str(row.get("id", name))
    if src in SOURCE_VALUE_RULES:
        k, t, rule, why = SOURCE_VALUE_RULES[src]
        return Triage(rid, name, src, cat, k, t, rule, why)
    if src == "other":
        if cat == "stretching":
            return Triage(rid, name, src, cat, "unusable", None, "R-STRETCH-OTHER", "stretch with source value 'other': no usable equipment information (and mobility is outside current exercise scope)")
        for rule, pat, k, t, why in RULES:
            if re.search(pat, low):
                return Triage(rid, name, src, cat, k, t, rule, why)
        return Triage(rid, name, src, cat, "ambiguous", None, "R-NO-RULE", "source value 'other' and no rule matches; needs a human")
    return Triage(rid, name, src, cat, "unusable", None, "R-NOT-UNKNOWN", "not an out-of-vocabulary value")


def triage_all(rows: Iterable[Mapping]) -> List[Triage]:
    return [triage_row(r) for r in rows if r.get("equipment") in ("other",) + tuple(SOURCE_VALUE_RULES)]

"""Compact exercise definitions -> full ExerciseRecord dicts. All output is labelled AI-curated / unreviewed / experimental."""
from __future__ import annotations

from typing import Dict, List, Sequence

from safety_core.models import REGIONS

_REG = {"lb": "lower_back", "sp": "spine_other", "nk": "neck", "mb": "mid_back", "sh": "shoulder", "el": "elbow", "wr": "wrist", "hd": "hand",
        "hp": "hip", "gr": "groin", "kn": "knee", "an": "ankle", "ft": "foot", "mt": "muscle_tendon"}
_LVL = {"0": "none", "1": "low", "2": "moderate", "3": "high"}
NOTE = "گردآوری‌شده توسط AI؛ بازبینی متخصص نشده است (تصمیم D-001). برآورد بار نواحی تقریبی است و فقط هسته‌ی ایمنی درباره‌ی پذیرش تصمیم می‌گیرد."


def loads(spec: str) -> Dict[str, str]:
    """'kn2 hp2 lb1' -> full region map (unlisted regions = none). Levels: 0 none, 1 low, 2 moderate, 3 high."""
    out = {r: "none" for r in REGIONS}
    for tok in spec.split():
        k, v = tok[:-1], tok[-1]
        if k not in _REG or v not in _LVL:
            raise ValueError(f"bad load token {tok!r}")
        out[_REG[k]] = _LVL[v]
    return out


def X(id: str, en: str, fa: str, pat: str, typ: str, eq: Sequence[str], diff: str, prim: Sequence[str], sec: Sequence[str], role: str, pp,
      ld: str, steps: Sequence[str], mistakes: Sequence[str], *, prog: Sequence[str] = (), reg: Sequence[str] = (), alt: Sequence[str] = (),
      caut: Sequence[tuple] = (), env: Sequence[str] = ("home", "gym"), contraction: str = "concentric_eccentric", desc: str = "",
      breathing: str = "", limits: Sequence[str] = (), aliases: Sequence[str] = ()) -> dict:
    return {
        "id": id, "name_en": en, "name_fa": fa, "aliases": list(aliases), "description": desc or fa, "primary_muscles": list(prim),
        "secondary_muscles": list(sec), "movement_pattern": pat, "exercise_type": typ, "equipment": list(eq), "difficulty": diff,
        "contraction": contraction, "range_of_motion": "", "instructions": list(steps), "common_mistakes": list(mistakes),
        "alternatives": list(alt), "regressions": list(reg), "progressions": list(prog), "region_loads": loads(ld), "role": role,
        "push_pull": pp, "supports_regions": [], "publication_status": "experimental", "expert_review": "pending",
        "safety_tags_status": "unreviewed_estimate", "evidence_level": "none", "is_sample": True,
        "sources": [{"source_id": "authored_unreviewed", "reference": "AI-curated general knowledge; no citations", "license_ok_for_commercial": True}],
        "last_reviewed": None, "contraindications": [], "cautions": [list(c) for c in caut], "license_status": "project_authored",
        "review_notes": [NOTE], "limitations": list(limits), "environments": list(env), "breathing": breathing,
    }

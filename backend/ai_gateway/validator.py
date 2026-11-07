"""OutputValidator: schema, forbidden content, allowed-exercise set (SAF-R009), sourced claims."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Tuple

FORBIDDEN = re.compile(
    r"you (have|suffer from)|i diagnose|guaranteed (cure|recovery)|will heal|take \d+ ?(mg|g)\b|push through (the )?pain|"
    r"ignore (the )?pain|تشخیص من|قطعاً خوب می‌شوید|درمان می‌شود|\d+ ?(میلی‌گرم|mg)|با درد ادامه دهید|درد را نادیده", re.I)
UNCERTAINTY = ("low", "medium", "high")


@dataclass(frozen=True)
class Validation:
    ok: bool
    reasons: Tuple[str, ...] = ()


def validate_output(payload: Any, allowed_exercise_codes: Iterable[str], valid_source_ids: Iterable[str] = ()) -> Validation:
    reasons = []
    if not isinstance(payload, Mapping):
        return Validation(False, ("schema:not-object",))
    text, ex, claims, unc = payload.get("text"), payload.get("exercises"), payload.get("claims"), payload.get("uncertainty")
    if not isinstance(text, str) or not text.strip():
        reasons.append("schema:text")
    if not isinstance(ex, list) or not all(isinstance(x, str) for x in ex):
        reasons.append("schema:exercises")
    if not isinstance(claims, list):
        reasons.append("schema:claims")
    if unc not in UNCERTAINTY:
        reasons.append("schema:uncertainty")
    if reasons:
        return Validation(False, tuple(reasons))
    if FORBIDDEN.search(text):
        reasons.append("forbidden-content")
    allowed = set(allowed_exercise_codes)
    for code in ex:
        if code not in allowed:
            reasons.append(f"SAF-R009:{code}")
    sources = set(valid_source_ids)
    for c in claims:
        if not isinstance(c, Mapping) or c.get("source_id") not in sources:
            reasons.append("unsourced-claim")
            break
        if FORBIDDEN.search(str(c.get("text", ""))):
            reasons.append("forbidden-content")
    return Validation(not reasons, tuple(dict.fromkeys(reasons)))

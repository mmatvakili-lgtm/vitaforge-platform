"""Deterministic canonical hashing of a SafetyRequest (reproducibility; no PHI in output)."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from enum import Enum
from typing import Any


def _canon(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _canon(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _canon(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, (list, tuple)):
        return [_canon(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    raise TypeError(f"unhashable type for canonicalisation: {type(obj).__name__}")


def inputs_hash(request: Any, rule_set_version: int) -> str:
    payload = {"request": _canon(request), "rule_set_version": rule_set_version}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def decision_id_from_hash(h: str) -> str:
    """Deterministic UUID-shaped id derived from the inputs hash (reproducibility, DOC-09 §13)."""
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

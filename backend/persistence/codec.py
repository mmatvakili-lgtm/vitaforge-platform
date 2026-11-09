"""Lossless JSON codec for store values and keys: tuples, sets and non-string dict keys survive a round trip; anything else raises."""
from __future__ import annotations

import dataclasses
import datetime as _dt
import enum
import importlib
import json
from typing import Any

# Only domain value types from these packages may be (de)serialised; nothing else is ever imported by name from stored data.
ALLOWED_PREFIXES = ("workout_engine.", "safety_core.", "nutrition_engine.", "exercise_catalog.", "ai_gateway.", "entitlements.")


class CodecError(TypeError):
    pass


def _check(cls) -> None:
    if not cls.__module__.startswith(ALLOWED_PREFIXES):
        raise CodecError(f"type {cls.__module__}.{cls.__qualname__} is not an allowed persistable domain type")


def _cls(ref: str):
    mod, _, name = ref.partition(":")
    if not mod.startswith(ALLOWED_PREFIXES):
        raise CodecError(f"refusing to load type from {mod}")
    obj = importlib.import_module(mod)
    for part in name.split("."):
        obj = getattr(obj, part)
    return obj


def _enc(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, _dt.datetime):
        return {"__dtm": v.isoformat()}
    if isinstance(v, _dt.date):
        return {"__date": v.isoformat()}
    if isinstance(v, enum.Enum):
        _check(type(v))
        return {"__e": f"{type(v).__module__}:{type(v).__qualname__}", "v": _enc(v.value)}
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        _check(type(v))
        return {"__dc": f"{type(v).__module__}:{type(v).__qualname__}", "f": {f.name: _enc(getattr(v, f.name)) for f in dataclasses.fields(v)}}
    if isinstance(v, tuple):
        return {"__t": [_enc(x) for x in v]}
    if isinstance(v, (set, frozenset)):
        return {"__s": sorted((_enc(x) for x in v), key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(v, list):
        return [_enc(x) for x in v]
    if isinstance(v, dict):
        if all(isinstance(k, str) and not k.startswith("__") for k in v) and not (set(v) <= {"__dc", "f"}):
            return {k: _enc(x) for k, x in v.items()}
        return {"__d": [[_enc(k), _enc(x)] for k, x in v.items()]}          # non-string keys / reserved names
    raise CodecError(f"cannot persist value of type {type(v).__name__}")


def _dec(v: Any) -> Any:
    if isinstance(v, list):
        return [_dec(x) for x in v]
    if isinstance(v, dict):
        if len(v) == 1 and "__date" in v:
            return _dt.date.fromisoformat(v["__date"])
        if len(v) == 1 and "__dtm" in v:
            return _dt.datetime.fromisoformat(v["__dtm"])
        if "__dc" in v and set(v) == {"__dc", "f"}:
            cls = _cls(v["__dc"])
            kw = {k: _dec(x) for k, x in v["f"].items()}
            init = {f.name for f in dataclasses.fields(cls) if f.init}
            obj = cls(**{k: x for k, x in kw.items() if k in init})
            for k, x in kw.items():
                if k not in init:
                    object.__setattr__(obj, k, x)
            return obj
        if "__e" in v and set(v) == {"__e", "v"}:
            return _cls(v["__e"])(_dec(v["v"]))
        if len(v) == 1 and "__t" in v:
            return tuple(_dec(x) for x in v["__t"])
        if len(v) == 1 and "__s" in v:
            return {_dec(x) for x in v["__s"]}
        if len(v) == 1 and "__d" in v:
            return {_dec(k): _dec(x) for k, x in v["__d"]}
        return {k: _dec(x) for k, x in v.items()}
    return v


def dumps(v: Any) -> str:
    return json.dumps(_enc(v), sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def loads(s: str) -> Any:
    return _dec(json.loads(s))

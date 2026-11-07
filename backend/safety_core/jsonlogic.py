"""Minimal, safe JSON-logic subset for data-driven rules.

Supported: var, ==, !=, >, >=, <, <=, in, and, or, !, not, truthy-literal.
Unknown operators raise RuleError (=> fail-safe at the engine level).
No eval(); no attribute access beyond dotted dict keys.
"""
from __future__ import annotations

from typing import Any, Mapping

from .errors import RuleError


def _var(path: str, data: Mapping[str, Any], default: Any = None) -> Any:
    cur: Any = data
    for part in str(path).split("."):
        if isinstance(cur, Mapping) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def apply(logic: Any, data: Mapping[str, Any]) -> Any:
    if not isinstance(logic, Mapping):
        return logic
    if len(logic) != 1:
        raise RuleError("rule node must have exactly one operator")
    (op, args), = logic.items()
    if op == "var":
        if isinstance(args, (list, tuple)):
            return _var(args[0], data, args[1] if len(args) > 1 else None)
        return _var(args, data)
    if not isinstance(args, (list, tuple)):
        args = [args]
    if op == "and":
        return all(bool(apply(a, data)) for a in args)
    if op == "or":
        return any(bool(apply(a, data)) for a in args)
    if op in ("!", "not"):
        return not bool(apply(args[0], data))
    vals = [apply(a, data) for a in args]
    try:
        if op == "==":
            return vals[0] == vals[1]
        if op == "!=":
            return vals[0] != vals[1]
        if op == ">":
            return vals[0] > vals[1]
        if op == ">=":
            return vals[0] >= vals[1]
        if op == "<":
            return vals[0] < vals[1]
        if op == "<=":
            return vals[0] <= vals[1]
        if op == "in":
            return vals[0] in vals[1]
    except TypeError:
        return False   # incomparable operands never match (conservative at rule level)
    raise RuleError(f"unsupported operator: {op!r}")

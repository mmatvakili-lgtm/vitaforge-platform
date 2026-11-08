"""Generate schema-valid (and deliberately invalid) sample payloads from OpenAPI schemas."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Tuple

UUID_A = "00000000-0000-4000-8000-000000000001"


def example(contract, schema: dict, depth: int = 0) -> Any:
    s = contract._rewrite(schema) if False else schema
    if "$ref" in s:
        return example(contract, contract.doc["components"]["schemas"][s["$ref"].split("/")[-1]], depth)
    if "oneOf" in s:
        for alt in s["oneOf"]:
            if alt.get("type") != "null":
                return example(contract, alt, depth)
    if "const" in s:
        return s["const"]
    if "enum" in s:
        return s["enum"][0]
    t = s.get("type")
    if isinstance(t, list):
        t = [x for x in t if x != "null"][0]
    if t == "object":
        out = {}
        for k in s.get("required", []):
            out[k] = example(contract, s["properties"][k], depth + 1)
        return out
    if t == "array":
        return [] if depth > 3 else [example(contract, s["items"], depth + 1)]
    if t == "integer":
        lo = s.get("minimum", s.get("exclusiveMinimum", 0) + 1 if "exclusiveMinimum" in s else 1)
        return max(lo, 1) if "maximum" not in s else min(max(lo, 1), s["maximum"])
    if t == "number":
        return float(s.get("minimum", 1) if "exclusiveMinimum" not in s else s["exclusiveMinimum"] + 1)
    if t == "boolean":
        return True
    fmt = s.get("format")
    if fmt == "uuid":
        return UUID_A
    if fmt == "email":
        return "user@example.com"
    if fmt == "date":
        return "1990-01-01"
    if fmt == "date-time":
        return "2026-01-01T00:00:00Z"
    if "pattern" in s:
        return "+989121234567"
    n = max(s.get("minLength", 1), 1)
    return "a" * n if n > 1 else "x"


def mutations(contract, schema: dict) -> List[Tuple[str, Any]]:
    """Invalid variants of a valid request body: each must be rejected by a conforming server."""
    base = example(contract, schema)
    resolved = schema
    if "$ref" in resolved:
        resolved = contract.doc["components"]["schemas"][resolved["$ref"].split("/")[-1]]
    out: List[Tuple[str, Any]] = []
    if resolved.get("type") != "object":
        return out
    props = resolved.get("properties", {})
    for k in resolved.get("required", []):
        b = copy.deepcopy(base); b.pop(k, None); out.append((f"missing:{k}", b))
    for k, ps in props.items():
        ps = contract.doc["components"]["schemas"][ps["$ref"].split("/")[-1]] if "$ref" in ps else ps
        b = copy.deepcopy(base)
        if "enum" in ps:
            b[k] = "__not_in_enum__"; out.append((f"enum:{k}", b)); continue
        if "const" in ps:
            b[k] = "__wrong__"; out.append((f"const:{k}", b)); continue
        t = ps.get("type")
        if t == "string":
            b[k] = 12345; out.append((f"type:{k}", b))
            if "minLength" in ps:
                b2 = copy.deepcopy(base); b2[k] = "a" * (ps["minLength"] - 1); out.append((f"minLength:{k}", b2))
            if "maxLength" in ps:
                b2 = copy.deepcopy(base); b2[k] = "a" * (ps["maxLength"] + 1); out.append((f"maxLength:{k}", b2))
            if ps.get("format") in ("uuid", "email", "date"):
                b2 = copy.deepcopy(base); b2[k] = "not-a-" + ps["format"]; out.append((f"format:{k}", b2))
        elif t in ("integer", "number"):
            b[k] = "abc"; out.append((f"type:{k}", b))
            for lim, delta in (("minimum", -1), ("maximum", 1)):
                if lim in ps:
                    b2 = copy.deepcopy(base); b2[k] = ps[lim] + delta; out.append((f"{lim}:{k}", b2))
            if "exclusiveMinimum" in ps:
                b2 = copy.deepcopy(base); b2[k] = ps["exclusiveMinimum"]; out.append((f"exclusiveMinimum:{k}", b2))
        elif t == "boolean":
            b[k] = "yes"; out.append((f"type:{k}", b))
        elif t == "array":
            b[k] = "notalist"; out.append((f"type:{k}", b))
        elif t == "object":
            b[k] = "notanobject"; out.append((f"type:{k}", b))
    if resolved.get("additionalProperties") is False:
        b = copy.deepcopy(base); b["__unknown_field__"] = 1; out.append(("additionalProperties", b))
    out.append(("body-not-object", ["x"]))
    return out

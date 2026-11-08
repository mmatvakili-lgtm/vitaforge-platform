"""Load the OpenAPI document and validate payloads against it (strict: required, type, format, enum, nullable,
additionalProperties, status codes, error envelope)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SPEC_PATH = Path(__file__).resolve().parents[2] / "docs" / "02-architecture" / "07-OPENAPI-SPECIFICATION.yaml"

_fmt = FormatChecker()


@_fmt.checks("date-time")
def _dt(v):
    if not isinstance(v, str):
        return True
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return False
    return "T" in v and (v.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", v) is not None)   # RFC 3339 requires an offset


@_fmt.checks("date")
def _d(v):
    if not isinstance(v, str):
        return True
    try:
        date.fromisoformat(v)
        return len(v) == 10
    except ValueError:
        return False


@_fmt.checks("email")
def _em(v):
    return not isinstance(v, str) or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) is not None


@_fmt.checks("uuid")
def _uuid(v):
    return not isinstance(v, str) or re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", v) is not None


@dataclass(frozen=True)
class Operation:
    id: str
    method: str
    path: str
    raw: Dict[str, Any]

    @property
    def secured(self) -> bool:
        return bool(self.raw.get("security"))

    @property
    def success_status(self) -> int:
        return min(int(s) for s in self.raw["responses"] if s.startswith("2"))

    @property
    def declared(self) -> List[int]:
        return sorted(int(s) for s in self.raw["responses"])

    @property
    def request_schema(self) -> Optional[dict]:
        rb = self.raw.get("requestBody")
        return rb["content"]["application/json"]["schema"] if rb else None

    @property
    def path_params(self) -> List[str]:
        return re.findall(r"\{(\w+)\}", self.path)


class Contract:
    def __init__(self, path: Path = SPEC_PATH):
        self.doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.version = self.doc["openapi"]
        res = Resource.from_contents({"$schema": "https://json-schema.org/draft/2020-12/schema", **self.doc})
        self.registry = Registry().with_resource("urn:spec", res)
        self.ops: List[Operation] = []
        for p, item in self.doc["paths"].items():
            for m, op in item.items():
                self.ops.append(Operation(op["x-id"], m.upper(), p, op))

    # -- schema validation -------------------------------------------------
    def _validator(self, schema: dict) -> Draft202012Validator:
        wrapped = {"$schema": "https://json-schema.org/draft/2020-12/schema", **self._rewrite(schema)}
        return Draft202012Validator(wrapped, registry=self.registry, format_checker=_fmt)

    def _rewrite(self, node):
        """Resolve '#/components/...' refs against the spec document; keep everything else untouched."""
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                out[k] = ("urn:spec" + v) if k == "$ref" and isinstance(v, str) and v.startswith("#") else self._rewrite(v)
            return out
        if isinstance(node, list):
            return [self._rewrite(x) for x in node]
        return node

    def errors(self, schema: dict, instance: Any) -> List[str]:
        v = self._validator(schema)
        return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message[:140]}" for e in sorted(v.iter_errors(instance), key=lambda e: list(e.absolute_path))]

    def violations(self, schema: dict, instance: Any) -> List[Tuple[str, str]]:
        """(path, rule) pairs only; never echoes submitted values (they may be secrets)."""
        v = self._validator(schema)
        return [("/".join(str(p) for p in e.absolute_path) or "<root>", e.validator) for e in sorted(v.iter_errors(instance), key=lambda e: list(e.absolute_path))]

    # -- spec self-consistency ---------------------------------------------
    def spec_dialect_problems(self) -> List[str]:
        """OpenAPI 3.0.x has no `const` and no type arrays; flag use of 3.1-only constructs under a 3.0 declaration."""
        problems: List[str] = []
        if not self.version.startswith("3.0"):
            return problems

        def walk(n, where):
            if isinstance(n, dict):
                if "const" in n:
                    problems.append(f"{where}: 'const' is not valid in OpenAPI {self.version}")
                for k in ("exclusiveMinimum", "exclusiveMaximum"):
                    if k in n and not isinstance(n[k], bool):
                        problems.append(f"{where}: numeric {k} is not valid in OpenAPI {self.version}")
                if isinstance(n.get("type"), list):
                    problems.append(f"{where}: type array is not valid in OpenAPI {self.version}")
                for k, v in n.items():
                    walk(v, f"{where}/{k}")
            elif isinstance(n, list):
                for i, x in enumerate(n):
                    walk(x, f"{where}[{i}]")
        walk(self.doc["components"]["schemas"], "#/components/schemas")
        return problems

    # -- response validation -----------------------------------------------
    def check_response(self, op: Operation, status: int, body: Any, content_type: str = "application/json") -> List[str]:
        problems: List[str] = []
        spec = op.raw["responses"].get(str(status))
        if spec is None:
            return [f"status {status} not declared (declared: {op.declared})"]
        if "content" in spec:
            if not content_type.startswith("application/json"):
                problems.append(f"content-type {content_type!r}")
            problems += self.errors(spec["content"]["application/json"]["schema"], body)
        return problems

    def check_request(self, op: Operation, body: Any) -> List[str]:
        sch = op.request_schema
        return self.errors(sch, body) if sch else []


@lru_cache(maxsize=1)
def contract() -> Contract:
    return Contract()

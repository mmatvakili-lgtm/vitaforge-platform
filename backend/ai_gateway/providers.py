"""Deterministic StubProvider for dev/test/CI. It is NOT a production model."""
from __future__ import annotations

from .ports import ModelRequest, ModelResponse, ProviderUnavailable


class StubProvider:
    code = "stub"
    external = False

    def __init__(self, payload=None, fail: bool = False):
        self._payload, self._fail = payload, fail

    def generate(self, req: ModelRequest) -> ModelResponse:
        if self._fail:
            raise ProviderUnavailable("stub down")
        names = list(req.context.get("exercise_names", []))
        payload = self._payload if self._payload is not None else {
            "text": "Plan explanation (stub).", "exercises": names, "claims": [], "uncertainty": "high"}
        return ModelResponse(payload=payload, provider=self.code, model_version="stub-1")

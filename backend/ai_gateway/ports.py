from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, Tuple


@dataclass(frozen=True)
class ModelRequest:
    prompt_id: str
    prompt_version: int
    user_text: str
    context: Mapping[str, Any]
    max_tokens: int = 512
    data_class: str = "non_health"      # non_health | health_redacted


@dataclass(frozen=True)
class ModelResponse:
    payload: Mapping[str, Any]
    provider: str
    model_version: str = "n/a"


class ProviderUnavailable(Exception):
    pass


class LLMProvider(Protocol):
    code: str
    external: bool

    def generate(self, req: ModelRequest) -> ModelResponse: ...

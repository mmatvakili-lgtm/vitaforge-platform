"""In-memory store: for unit tests and local dev ONLY (never a production adapter)."""
from __future__ import annotations

import itertools
from typing import Any, Dict, List


class InMemoryStore:
    def __init__(self):
        self.users: Dict[str, dict] = {}
        self.by_email: Dict[str, str] = {}
        self.sessions: Dict[str, dict] = {}
        self.consents: List[dict] = []
        self.profiles: Dict[str, dict] = {}
        self.health: Dict[str, dict] = {}
        self.catalog: Dict[str, Any] = {}
        self.relations: Dict[str, list] = {}
        self.plans: Dict[str, List[dict]] = {}
        self.workout_sessions: Dict[str, dict] = {}
        self.audit: List[dict] = []
        self._ids = itertools.count(1)

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{next(self._ids)}"

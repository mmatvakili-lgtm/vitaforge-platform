"""PersistentStore: dict/list-compatible collections with an identity map, dirty detection by serialisation compare and
all-or-nothing transactions.

  with store.transaction():     # begin ... flush changed values ... commit; on exception: rollback AND drop all cached state
      service.do_something()

Writes made outside a transaction live only in memory (never persisted): production entry points MUST wrap every request.
Point reads (`get`, `[]`, `in`) hit the backend by key; iteration (`values/items/len`) loads the whole collection once per transaction."""
from __future__ import annotations

import contextlib
from collections.abc import MutableMapping, MutableSequence
from typing import Any, Callable, Dict, Iterator, Optional

from . import codec


class StoreError(Exception):
    pass


def _owner_default(coll: str, key: Any, value: Any) -> Optional[str]:
    """User ownership column used for query-level isolation / per-user erase."""
    if coll == "users":
        return key if isinstance(key, str) else None
    if isinstance(value, dict):
        u = value.get("user")
        if isinstance(u, str):
            return u
    if isinstance(key, str) and coll in OWNER_KEYED:
        return key
    if isinstance(key, tuple) and key and isinstance(key[0], str) and coll in OWNER_KEYED:
        return key[0]
    return None


OWNER_KEYED = {"profiles", "health", "plans", "measurements", "pain_logs", "metrics", "symptoms", "cond_meta", "subs", "nutrition_profiles", "verification",
               "meals", "water", "user_prices", "shopping_state"}

MAPS = ("catalog", "relations", "users", "by_email", "sessions", "profiles", "health", "plans", "workout_sessions", "exercise_meta", "rule_sets", "verification", "resets",
        "subs", "privacy_requests", "pain_logs", "metrics", "measurements", "cond_meta", "symptoms", "nutrition_profiles", "foods", "recipes", "price_quotes", "outbox", "reset_index", "mail_limits", "captured_mail",
        "meals", "water", "user_prices", "shopping_state", "tg_tokens", "tg_links", "tg_limits")
LISTS = ("consents", "audit", "erasure_audit", "grants")


class PersistentMap(MutableMapping):
    def __init__(self, store: "PersistentStore", coll: str):
        self._st, self._coll = store, coll
        self._reset()

    def _reset(self):
        self._cache: Dict[str, Any] = {}          # encoded key -> live value
        self._snap: Dict[str, str] = {}           # encoded key -> serialisation at load/flush time
        self._keys: Dict[str, Any] = {}           # encoded key -> original key
        self._deleted: set = set()
        self._full = False

    @staticmethod
    def _k(key: Any) -> str:
        return codec.dumps(key)

    def __getitem__(self, key):
        ek = self._k(key)
        if ek in self._cache:
            return self._cache[ek]
        if ek in self._deleted:
            raise KeyError(key)
        raw = self._st.backend.load(self._coll, ek)
        if raw is None:
            raise KeyError(key)
        v = codec.loads(raw)
        self._cache[ek], self._snap[ek], self._keys[ek] = v, raw, key
        return v

    def __setitem__(self, key, value):
        ek = self._k(key)
        self._cache[ek], self._keys[ek] = value, key
        self._deleted.discard(ek)
        codec.dumps(value)                              # fail loudly NOW if the value cannot be persisted

    def __delitem__(self, key):
        self[key]                                       # KeyError if absent
        ek = self._k(key)
        self._cache.pop(ek, None)
        self._snap.pop(ek, None)
        self._deleted.add(ek)

    def _load_all(self):
        if self._full:
            return
        for ek, raw in self._st.backend.scan(self._coll):
            if ek in self._cache or ek in self._deleted:
                continue
            self._cache[ek], self._snap[ek], self._keys[ek] = codec.loads(raw), raw, codec.loads(ek)
        self._full = True

    def __iter__(self) -> Iterator:
        self._load_all()
        return iter([self._keys[ek] for ek in list(self._cache)])

    def __len__(self):
        self._load_all()
        return len(self._cache)

    def clear(self):
        self._load_all()
        for ek in list(self._cache):
            self._deleted.add(ek)
        self._cache.clear(); self._snap.clear()

    def _flush(self):
        for ek in self._deleted:
            self._st.backend.delete(self._coll, ek)
        for ek, v in self._cache.items():
            raw = codec.dumps(v)
            if self._snap.get(ek) != raw:
                self._st.backend.save(self._coll, ek, raw, self._st.owner_of(self._coll, self._keys[ek], v))
                self._snap[ek] = raw
        self._deleted.clear()


class PersistentList(MutableSequence):
    """Ordered list stored as rows keyed by position. Appends and in-place item edits are tracked; structural rewrites replace all rows."""
    def __init__(self, store: "PersistentStore", coll: str):
        self._st, self._coll = store, coll
        self._reset()

    def _reset(self):
        self._items: Optional[list] = None
        self._snap: list = []

    def _load(self):
        if self._items is None:
            rows = self._st.backend.scan(self._coll)
            self._snap = [raw for _, raw in rows]
            self._items = [codec.loads(raw) for _, raw in rows]
        return self._items

    def __getitem__(self, i):
        return self._load()[i]

    def __setitem__(self, i, v):
        self._load()[i] = v

    def __delitem__(self, i):
        del self._load()[i]

    def __len__(self):
        return len(self._load())

    def insert(self, i, v):
        codec.dumps(v)
        self._load().insert(i, v)

    def _flush(self):
        if self._items is None:
            return
        raws = [codec.dumps(v) for v in self._items]
        if raws == self._snap:
            return
        if raws[:len(self._snap)] == self._snap:                         # pure append: write only new rows
            start = len(self._snap)
        else:                                                           # rewritten: replace everything
            for ek, _ in self._st.backend.scan(self._coll):
                self._st.backend.delete(self._coll, ek)
            start = 0
        for n in range(start, len(raws)):
            self._st.backend.save(self._coll, f"{n:012d}", raws[n], self._st.owner_of(self._coll, n, self._items[n]))
        self._snap = raws


class PersistentStore:
    """Drop-in for InMemoryStore. Every collection is persisted (domain dataclasses/enums via codec allow-list); callables are not persistable."""
    def __init__(self, backend, owner_of: Callable = _owner_default):
        object.__setattr__(self, "backend", backend)
        object.__setattr__(self, "owner_of", owner_of)
        object.__setattr__(self, "_colls", {})
        for n in MAPS:
            self._colls[n] = PersistentMap(self, n)
            self.__dict__[n] = self._colls[n]                     # makes `store.__dict__.setdefault(name, {})` return the persistent object
        for n in LISTS:
            self._colls[n] = PersistentList(self, n)
            self.__dict__[n] = self._colls[n]
        self._depth = 0

    def __setattr__(self, name, value):
        if name in ("backend", "owner_of", "_colls") or name not in self._colls:
            return object.__setattr__(self, name, value)
        c = self._colls[name]                                      # `store.sessions = {...}` rewrites the persistent collection
        if isinstance(c, PersistentMap):
            items = dict(value)
            c.clear()
            for k, v in items.items():
                c[k] = v
        else:
            items = list(value)
            c._load()
            c._items[:] = items

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{self.backend.next_seq('ids')}"

    @contextlib.contextmanager
    def transaction(self):
        """Nestable. Outermost exit commits (after flushing) or rolls back and discards every cached object."""
        if self._depth:
            self._depth += 1
            try:
                yield self
            finally:
                self._depth -= 1
            return
        self.backend.begin()
        self._depth = 1
        try:
            yield self
            for c in self._colls.values():
                c._flush()
            self.backend.commit()
        except BaseException:
            self.backend.rollback()
            for c in self._colls.values():
                c._reset()
            raise
        finally:
            self._depth = 0
            for c in self._colls.values():                          # next request re-reads committed state; no cross-request caching
                c._reset()

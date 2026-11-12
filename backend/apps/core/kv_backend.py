"""Django ORM backend for persistence.PersistentStore (PostgreSQL in production; SQLite also works for local runs).
NEEDS LOCAL VERIFICATION: written without a Django runtime. Contract = persistence/sqlite_backend.py; the same conformance tests
(persistence/tests/test_store.py) run against this class when Django is installed (apps/core/tests)."""
from __future__ import annotations

from typing import Iterable, Optional, Tuple

from django.db import connections, transaction

from .models import IdSequence, KVRecord


class DjangoBackend:
    def __init__(self, using: str = "default", namespace: str = ""):
        """`namespace` prefixes every collection name: production uses "" ; tests give each store its own namespace so several stores
        (e.g. a Harness plus a second Harness inside happy_path) can share one test database without seeing each other's data."""
        self.using = using
        self.ns = f"{namespace}:" if namespace else ""
        self._atomic = None

    def _c(self, coll: str) -> str:
        return self.ns + coll

    # --- transaction control (the store calls these once per request)
    def begin(self):
        self._atomic = transaction.atomic(using=self.using)
        self._atomic.__enter__()

    def commit(self):
        a, self._atomic = self._atomic, None
        a.__exit__(None, None, None)

    def rollback(self):
        if self._atomic is not None:
            a, self._atomic = self._atomic, None
            transaction.set_rollback(True, using=self.using)
            a.__exit__(None, None, None)

    # --- data access
    def _qs(self):
        return KVRecord.objects.using(self.using)

    def load(self, coll: str, key: str) -> Optional[str]:
        qs = self._qs().filter(coll=self._c(coll), k=key)
        if self._atomic is not None and connections[self.using].features.has_select_for_update:
            qs = qs.select_for_update()                       # row lock: serialises concurrent read-modify-write of the same record (no lost updates)
        return qs.values_list("data", flat=True).first()

    def scan(self, coll: str) -> Iterable[Tuple[str, str]]:
        return list(self._qs().filter(coll=self._c(coll)).order_by("id").values_list("k", "data"))

    def save(self, coll: str, key: str, data: str, owner: Optional[str]):
        self._qs().update_or_create(coll=self._c(coll), k=key, defaults={"data": data, "owner": owner})

    def delete(self, coll: str, key: str):
        self._qs().filter(coll=self._c(coll), k=key).delete()

    def delete_owner(self, coll: str, owner: str):
        self._qs().filter(coll=self._c(coll), owner=owner).delete()

    def next_seq(self, name: str) -> int:
        row, _ = IdSequence.objects.using(self.using).select_for_update().get_or_create(name=self.ns + name)
        row.n += 1
        row.save(update_fields=["n"])
        return row.n

    # --- backup / restore support (see persistence/backup.py). NEEDS LOCAL VERIFICATION against a real database.
    def dump_all(self):
        return list(self._qs().filter(coll__startswith=self.ns).order_by("id").values_list("coll", "k", "owner", "data")) if self.ns else \
            list(self._qs().order_by("id").values_list("coll", "k", "owner", "data"))

    def dump_seqs(self):
        return dict(IdSequence.objects.using(self.using).values_list("name", "n"))

    def is_empty(self) -> bool:
        return not self._qs().exists()

    def wipe(self):
        self._qs().all().delete()
        IdSequence.objects.using(self.using).all().delete()

    def restore_row(self, coll, key, owner, data):
        self._qs().update_or_create(coll=coll, k=key, defaults={"data": data, "owner": owner})

    def restore_seq(self, name, n):
        IdSequence.objects.using(self.using).update_or_create(name=name, defaults={"n": n})

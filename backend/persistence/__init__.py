"""Persistent unit-of-work store: same attribute API as `app_services.store.InMemoryStore`, backed by a transactional Backend
(SQLite for local/tests, Django ORM -> PostgreSQL in production). Framework-neutral."""
from .store import PersistentStore, StoreError
from .sqlite_backend import SqliteBackend

__all__ = ["PersistentStore", "SqliteBackend", "StoreError"]

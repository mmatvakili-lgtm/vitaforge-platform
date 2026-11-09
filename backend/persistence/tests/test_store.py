import pytest

from persistence import PersistentStore, SqliteBackend

from .conformance import *          # noqa: F401,F403  (shared conformance suite)


@pytest.fixture
def new_store(tmp_path):
    path = str(tmp_path / "store.sqlite")
    return lambda: PersistentStore(SqliteBackend(path))


def test_owner_column_is_set_for_user_isolation_queries(new_store):
    s = new_store()
    with s.transaction():
        s.users["u1"] = {"id": "u1"}
        s.sessions["h"] = {"user": "u1", "id": "s"}
        s.plans["u2"] = [{"v": 1}]
    rows = dict(((c, k), o) for c, k, o in s.backend.db.execute("SELECT coll,k,owner FROM kv"))
    assert rows[("users", '"u1"')] == "u1" and rows[("sessions", '"h"')] == "u1" and rows[("plans", '"u2"')] == "u2"


def test_caches_do_not_leak_between_transactions(new_store):
    s = new_store()
    with s.transaction():
        s.users["u"] = {"v": 1}
    with s.transaction():
        s.users["u"]["v"] = 2
    s.backend.db.execute("UPDATE kv SET data='{\"v\":99}' WHERE coll='users'")           # external writer between requests
    with s.transaction():
        assert s.users["u"]["v"] == 99

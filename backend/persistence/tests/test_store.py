import pytest

from persistence import PersistentStore, SqliteBackend, StoreError
from persistence import codec
from persistence.codec import CodecError


def mk(path=":memory:"):
    return PersistentStore(SqliteBackend(path))


def test_codec_roundtrip_preserves_tuples_sets_and_int_keys():
    v = {"a": (1, 2, {"x": (3,)}), 9: [1, {2, 3}], ("u", 1): "k", "__t": "reserved-key-ok"}
    assert codec.loads(codec.dumps(v)) == v
    assert type(codec.loads(codec.dumps((1, 2)))) is tuple
    with pytest.raises(CodecError):
        codec.dumps({"f": lambda: 1})


def test_commit_persists_across_restart(tmp_path):
    p = str(tmp_path / "db.sqlite")
    s = mk(p)
    with s.transaction():
        s.users["u1"] = {"id": "u1", "email": "a@b.co", "fails": 0}
        s.by_email["a@b.co"] = "u1"
        s.consents.append({"user": "u1", "type": "health_data", "granted": True})
        s.cond_meta[("u1", 7)] = {"note": "tuple key"}
        s.rule_sets[9] = {"status": "draft"}
    s2 = mk(p)                                            # "restart": brand-new store object on the same database file
    with s2.transaction():
        assert s2.users["u1"]["email"] == "a@b.co" and s2.by_email["a@b.co"] == "u1"
        assert list(s2.consents) == [{"user": "u1", "type": "health_data", "granted": True}]
        assert s2.cond_meta[("u1", 7)] == {"note": "tuple key"} and s2.rule_sets[9] == {"status": "draft"}


def test_rollback_discards_everything_including_nested_mutation():
    s = mk()
    with s.transaction():
        s.users["u1"] = {"id": "u1", "fails": 0}
    with pytest.raises(RuntimeError):
        with s.transaction():
            s.users["u1"]["fails"] = 5                    # in-place mutation of a loaded value
            s.users["u2"] = {"id": "u2"}
            s.consents.append({"user": "u1"})
            raise RuntimeError("boom")
    with s.transaction():
        assert s.users["u1"]["fails"] == 0 and "u2" not in s.users and len(s.consents) == 0


def test_in_place_mutation_is_persisted_without_explicit_save():
    s = mk()
    with s.transaction():
        s.users["u1"] = {"id": "u1", "fails": 0}
    with s.transaction():
        s.users["u1"]["fails"] += 1
        s.users["u1"].setdefault("prefs", {})["theme"] = "dark"
    with s.transaction():
        assert s.users["u1"]["fails"] == 1 and s.users["u1"]["prefs"] == {"theme": "dark"}


def test_nested_transaction_failure_rolls_back_outer_too():
    s = mk()
    with pytest.raises(ValueError):
        with s.transaction():
            s.users["u1"] = {"id": "u1"}
            with s.transaction():
                s.users["u2"] = {"id": "u2"}
                raise ValueError()
    with s.transaction():
        assert len(s.users) == 0


def test_delete_pop_and_replace_assignment():
    s = mk()
    with s.transaction():
        for i in range(3):
            s.sessions[f"h{i}"] = {"user": "u1" if i < 2 else "u2", "id": f"s{i}"}
    with s.transaction():
        s.sessions = {h: x for h, x in s.sessions.items() if x["user"] != "u1"}          # same pattern as erase_account
        assert s.sessions.pop("nope", None) is None
    with s.transaction():
        assert list(s.sessions) == ["h2"]
        del s.sessions["h2"]
        with pytest.raises(KeyError):
            s.sessions["h2"]
    with s.transaction():
        assert len(s.sessions) == 0


def test_list_append_only_and_rewrite():
    s = mk()
    with s.transaction():
        s.consents.append({"user": "a", "n": 1}); s.consents.append({"user": "b", "n": 2})
    with s.transaction():
        s.consents.append({"user": "a", "n": 3})
    with s.transaction():
        assert [c["n"] for c in s.consents] == [1, 2, 3]
        s.consents = [c for c in s.consents if c["user"] != "a"]                          # erase pattern
    with s.transaction():
        assert [c["n"] for c in s.consents] == [2]


def test_ids_are_unique_across_restart(tmp_path):
    p = str(tmp_path / "d.sqlite")
    a = mk(p)
    with a.transaction():
        ids = {a.new_id("usr"), a.new_id("usr")}
    b = mk(p)
    with b.transaction():
        ids |= {b.new_id("usr")}
    assert len(ids) == 3


def test_unpersistable_value_fails_loudly_at_assignment():
    s = mk()
    with pytest.raises(CodecError):
        with s.transaction():
            s.users["u"] = {"cb": lambda: 1}


def test_owner_column_is_set_for_user_isolation_queries():
    s = mk()
    with s.transaction():
        s.users["u1"] = {"id": "u1"}
        s.sessions["h"] = {"user": "u1", "id": "s"}
        s.plans["u2"] = [{"v": 1}]
    rows = dict(((c, k), o) for c, k, o in s.backend.db.execute("SELECT coll,k,owner FROM kv"))
    assert rows[("users", '"u1"')] == "u1" and rows[("sessions", '"h"')] == "u1" and rows[("plans", '"u2"')] == "u2"


def test_caches_do_not_leak_between_transactions():
    s = mk()
    with s.transaction():
        s.users["u"] = {"v": 1}
    with s.transaction():
        s.users["u"]["v"] = 2
    s.backend.db.execute("UPDATE kv SET data='{\"v\":99}' WHERE coll='users'")           # external writer between requests
    with s.transaction():
        assert s.users["u"]["v"] == 99

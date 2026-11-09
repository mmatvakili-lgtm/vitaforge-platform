"""End-to-end persistence on a real (file) SQLite database through the real HTTP adapter: restart survival, rollback on server error,
user isolation, erase. (PostgreSQL runs the same store through the Django backend; see docs/WINDOWS_SETUP.md.)"""
import pytest

from contract.harness import PASSWORD, Harness
from persistence import PersistentStore, SqliteBackend


def boot(path):
    return Harness(store=PersistentStore(SqliteBackend(path)))


def test_accounts_sessions_profile_plan_survive_restart(tmp_path):
    p = str(tmp_path / "vf.sqlite")
    h = boot(p)
    t = h.login("keep@ex.com"); h.onboard(t)
    assert h.call("POST", "/onboarding/complete", token=t).status == 200
    plan = h.call("POST", "/workouts/generate", {}, token=t).body
    assert plan["plan"]
    h2 = boot(p)                                                             # server restart: new process state, same database
    assert h2.call("GET", "/profile", token=t).status == 200                 # the SAME session token still works
    again = h2.call("POST", "/auth/login", {"identifier": "keep@ex.com", "password": PASSWORD})
    assert again.status == 200
    hist = h2.call("GET", "/workouts/plans", token=t) if h2.op_for("GET", "/workouts/plans") else None
    assert hist is None or hist.status == 200
    with h2.store.transaction():
        assert len(h2.store.plans) == 1 and len(h2.store.consents) >= 1


def test_lockout_counter_commits_even_though_login_fails(tmp_path):
    h = boot(str(tmp_path / "l.sqlite"))
    h.register("lock@ex.com")
    for _ in range(5):
        assert h.call("POST", "/auth/login", {"identifier": "lock@ex.com", "password": "Wrong-pass-1"}).status == 401
    assert h.call("POST", "/auth/login", {"identifier": "lock@ex.com", "password": PASSWORD}).status == 423   # state from failed requests persisted


def test_unexpected_server_error_rolls_back_the_whole_request(tmp_path, monkeypatch):
    h = boot(str(tmp_path / "r.sqlite"))
    t = h.login("rb@ex.com")
    before = h.call("GET", "/profile", token=t).body
    def boom(*a, **k):
        h.store.users[next(iter(h.store.users))]["locale"] = "en"            # partial write ...
        raise RuntimeError("injected failure")                               # ... then crash
    monkeypatch.setattr(h.app.m, "patch_profile", boom)
    r = h.call("PATCH", "/profile", {"language": "en"}, token=t, check=False)
    assert r.status == 500
    monkeypatch.undo()
    assert h.call("GET", "/profile", token=t).body == before                 # nothing from the failed request was committed


def test_user_isolation_survives_persistence(tmp_path):
    p = str(tmp_path / "i.sqlite")
    h = boot(p)
    a, b = h.login("a@ex.com"), h.login("b@ex.com")
    h.onboard(a); h.call("POST", "/onboarding/complete", token=a)
    pa = h.call("POST", "/workouts/generate", {}, token=a).body
    sid = pa["plan"]["days"][0]["day_id"]
    h2 = boot(p)
    assert h2.call("POST", "/workouts/sessions", {"day_id": sid}, token=b, check=False).status in (404, 403, 409, 422)
    with h2.store.transaction():
        owners = {o for (o,) in h2.store.backend.db.execute("SELECT DISTINCT owner FROM kv WHERE coll='plans'")}
        assert len(owners) == 1


def test_erase_account_removes_rows_from_the_database(tmp_path):
    p = str(tmp_path / "e.sqlite")
    h = boot(p)
    t = h.login("gone@ex.com"); h.onboard(t); h.call("POST", "/onboarding/complete", token=t)
    h.call("POST", "/workouts/generate", {}, token=t)
    r = h.call("POST", "/privacy/delete", {"password": PASSWORD, "confirm": True}, token=t)
    assert r.status == 202 or r.status == 200, (r.status, r.body)
    h2 = boot(p)
    rows = h2.store.backend.db.execute("SELECT coll, data FROM kv WHERE coll IN ('users','profiles','health','plans','by_email','sessions')").fetchall()
    assert rows == []                                                         # nothing left of the user in the persisted tables
    assert h2.call("GET", "/profile", token=t, check=False).status == 401

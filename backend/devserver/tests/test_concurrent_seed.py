"""First page loads arrive in parallel on a fresh database: seeding must happen once, without errors (regression: 'server error' + profile not saved)."""
import threading

from devserver.bootstrap import build_app
from persistence import PersistentStore
from persistence.sqlite_backend import SqliteBackend


def test_parallel_first_requests_seed_once_without_errors(tmp_path):
    path = str(tmp_path / "vf.db")
    errors, counts = [], []

    def worker():
        try:
            app = build_app(PersistentStore(SqliteBackend(path)), dev_content=True, dev_mode=True)
            counts.append((len(app.store.catalog), len(app.store.foods), len(app.store.recipes)))
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))

    ts = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errors, errors
    assert len(set(counts)) == 1 and counts[0][0] >= 229 and counts[0][1] >= 50 and counts[0][2] >= 25

"""SQLite backend (stdlib). Used for local runs and for testing the store's real persistence/transaction semantics."""
from __future__ import annotations

import sqlite3
from typing import Iterable, Optional, Tuple


class SqliteBackend:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)    # explicit BEGIN/COMMIT below
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("CREATE TABLE IF NOT EXISTS kv (coll TEXT NOT NULL, k TEXT NOT NULL, owner TEXT, data TEXT NOT NULL, PRIMARY KEY (coll, k))")
        self.db.execute("CREATE INDEX IF NOT EXISTS kv_owner ON kv (coll, owner)")
        self.db.execute("CREATE TABLE IF NOT EXISTS seq (name TEXT PRIMARY KEY, n INTEGER NOT NULL)")
        self._in_tx = False

    def begin(self):
        self.db.execute("BEGIN IMMEDIATE")
        self._in_tx = True

    def commit(self):
        self.db.execute("COMMIT")
        self._in_tx = False

    def rollback(self):
        if self._in_tx:
            self.db.execute("ROLLBACK")
            self._in_tx = False

    def load(self, coll: str, key: str) -> Optional[str]:
        r = self.db.execute("SELECT data FROM kv WHERE coll=? AND k=?", (coll, key)).fetchone()
        return r[0] if r else None

    def scan(self, coll: str) -> Iterable[Tuple[str, str]]:
        return self.db.execute("SELECT k, data FROM kv WHERE coll=? ORDER BY rowid", (coll,)).fetchall()

    def save(self, coll: str, key: str, data: str, owner: Optional[str]):
        self.db.execute("INSERT INTO kv (coll,k,owner,data) VALUES (?,?,?,?) ON CONFLICT(coll,k) DO UPDATE SET data=excluded.data, owner=excluded.owner",
                        (coll, key, owner, data))

    def delete(self, coll: str, key: str):
        self.db.execute("DELETE FROM kv WHERE coll=? AND k=?", (coll, key))

    def delete_owner(self, coll: str, owner: str):
        self.db.execute("DELETE FROM kv WHERE coll=? AND owner=?", (coll, owner))

    def next_seq(self, name: str) -> int:
        self.db.execute("INSERT INTO seq (name,n) VALUES (?,1) ON CONFLICT(name) DO UPDATE SET n=n+1", (name,))
        return self.db.execute("SELECT n FROM seq WHERE name=?", (name,)).fetchone()[0]

    # --- backup / restore support (see persistence/backup.py)
    def dump_all(self):
        return self.db.execute("SELECT coll, k, owner, data FROM kv ORDER BY rowid").fetchall()

    def dump_seqs(self):
        return dict(self.db.execute("SELECT name, n FROM seq").fetchall())

    def is_empty(self) -> bool:
        return self.db.execute("SELECT 1 FROM kv LIMIT 1").fetchone() is None

    def wipe(self):
        self.db.execute("DELETE FROM kv"); self.db.execute("DELETE FROM seq")

    def restore_row(self, coll, key, owner, data):
        self.save(coll, key, data, owner)

    def restore_seq(self, name, n):
        self.db.execute("INSERT INTO seq (name,n) VALUES (?,?) ON CONFLICT(name) DO UPDATE SET n=excluded.n", (name, n))

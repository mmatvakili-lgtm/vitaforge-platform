import io
import json
import os
import stat

import pytest

from persistence import SqliteBackend
from persistence.backup import BackupError, build_backup, parse_backup, restore_backup, write_backup


def fill(b):
    b.begin()
    b.save("users", "u1", '{"email":"a@x.com"}', "u1")
    b.save("meals", "u1", '[{"kcal":100}]', "u1")
    b.save("sessions", "h1", '{"user":"u1"}', "u1")
    b.save("captured_mail", "m1", '{}', None)
    b.next_seq("prq"); b.next_seq("prq")
    b.commit()


def test_backup_excludes_sessions_and_restores_exactly():
    a = SqliteBackend(); fill(a)
    doc = build_backup(a, now=1)
    colls = {r[0] for r in doc["rows"]}
    assert colls == {"users", "meals"} and doc["sequences"] == {"prq": 2}
    b = SqliteBackend()
    b.begin(); c = restore_backup(b, io.StringIO(json.dumps(doc))); b.commit()
    assert c == {"rows": 2, "sequences": 1}
    assert b.load("users", "u1") == '{"email":"a@x.com"}' and b.load("meals", "u1") == '[{"kcal":100}]'
    assert b.load("sessions", "h1") is None
    assert b.next_seq("prq") == 3                      # id sequences continue, never reused


def test_tampering_and_wrong_files_are_rejected_before_any_write():
    a = SqliteBackend(); fill(a)
    doc = build_backup(a, now=1)
    doc["rows"][0][3] = '{"email":"evil@x.com"}'
    b = SqliteBackend()
    with pytest.raises(BackupError, match="checksum"):
        restore_backup(b, io.StringIO(json.dumps(doc)))
    assert b.is_empty()
    for bad in ("not json", json.dumps({"format": "other"}), json.dumps({"format": "vitaforge-backup", "version": 99})):
        with pytest.raises(BackupError):
            parse_backup(io.StringIO(bad))


def test_restore_refuses_non_empty_target_unless_replace():
    a = SqliteBackend(); fill(a)
    text = json.dumps(build_backup(a, now=1))
    t = SqliteBackend(); t.begin(); t.save("users", "other", "{}", "other"); t.commit()
    with pytest.raises(BackupError, match="not empty"):
        restore_backup(t, io.StringIO(text))
    assert t.load("users", "other") == "{}"
    t.begin(); restore_backup(t, io.StringIO(text), replace=True); t.commit()
    assert t.load("users", "other") is None and t.load("users", "u1")


def test_file_is_owner_only_and_never_overwritten(tmp_path):
    a = SqliteBackend(); fill(a)
    p = str(tmp_path / "b.json")
    r = write_backup(a, p)
    assert r["rows"] == 2
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    with pytest.raises(FileExistsError):
        write_backup(a, p)

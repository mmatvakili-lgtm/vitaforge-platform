"""Backup / restore of the whole persistent store as one self-describing, checksummed JSON document.

Why this format: it is backend-neutral (SQLite and PostgreSQL via the Django ORM backend produce/consume the same file), human-inspectable,
and verifiable before anything is written. It is NOT encrypted (stdlib only): the file contains health data and password hashes, so callers
must write it with owner-only permissions and store it encrypted at rest (see docs). Login sessions are deliberately not backed up: a
restored system forces everyone to sign in again."""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import IO, Any, Dict, List

FORMAT = "vitaforge-backup"
VERSION = 1
EXCLUDED_COLLECTIONS = frozenset({"sessions", "captured_mail"})      # session tokens are not worth carrying over; captured mail is dev-only


class BackupError(Exception):
    pass


def _digest(rows: List[list], seqs: Dict[str, int]) -> str:
    return hashlib.sha256(json.dumps([rows, seqs], sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def build_backup(backend, now: int | None = None) -> Dict[str, Any]:
    rows = [[c, k, o, d] for c, k, o, d in backend.dump_all() if c.split(":")[-1] not in EXCLUDED_COLLECTIONS]
    seqs = {str(k): int(v) for k, v in backend.dump_seqs().items()}
    return {"format": FORMAT, "version": VERSION, "created_at": int(time.time() if now is None else now),
            "counts": {"rows": len(rows), "sequences": len(seqs)}, "sha256": _digest(rows, seqs), "rows": rows, "sequences": seqs}


def write_backup(backend, path: str, now: int | None = None) -> Dict[str, Any]:
    doc = build_backup(backend, now)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)     # owner-only; never overwrites an existing backup
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False)
    return {"path": path, **doc["counts"], "sha256": doc["sha256"]}


def parse_backup(fp: IO[str]) -> Dict[str, Any]:
    try:
        doc = json.load(fp)
    except ValueError as e:
        raise BackupError("not a valid backup file") from e
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise BackupError("not a VitaForge backup")
    if doc.get("version") != VERSION:
        raise BackupError(f"unsupported backup version {doc.get('version')!r}")
    rows, seqs = doc.get("rows"), doc.get("sequences")
    if not isinstance(rows, list) or not isinstance(seqs, dict) or any(not (isinstance(r, list) and len(r) == 4) for r in rows):
        raise BackupError("malformed backup")
    if doc.get("sha256") != _digest(rows, seqs):
        raise BackupError("checksum mismatch: the file is corrupted or was modified")
    if doc.get("counts") != {"rows": len(rows), "sequences": len(seqs)}:
        raise BackupError("row counts do not match")
    return doc


def restore_backup(backend, fp: IO[str], replace: bool = False) -> Dict[str, int]:
    """Verifies the whole file first. Refuses to touch a non-empty database unless `replace` is set. The caller wraps this in one transaction."""
    doc = parse_backup(fp)
    if not backend.is_empty():
        if not replace:
            raise BackupError("the target database is not empty (use replace to overwrite it)")
        backend.wipe()
    for c, k, o, d in doc["rows"]:
        backend.restore_row(c, k, o, d)
    for name, n in doc["sequences"].items():
        backend.restore_seq(name, int(n))
    return doc["counts"]

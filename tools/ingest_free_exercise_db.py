#!/usr/bin/env python3
"""Reproducible, legally cautious ingestion of yuhonas/free-exercise-db into STAGING (never into the loadable catalogue).

Usage: python3 tools/ingest_free_exercise_db.py [path-to-exercises.json]   (downloads from GitHub raw when no path is given)

Output: backend/exercise_catalog/data/staging/free_exercise_db.json  + .manifest.json (url, retrieval date, sha256, counts, licence findings).
Facts recorded from the upstream README (read 2026-11-10): declares "Open Public Domain" / Unlicense badge; images' licence not stated;
no LICENSE file found at repo root; upstream wrkout/exercises.json also has no LICENSE file. => licence status stays UNVERIFIED:
every record is pending_review, never published, images are NOT referenced, and no Persian names are invented.
"""
import dataclasses
import hashlib
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from exercise_catalog.importer import import_free_exercise_db  # noqa: E402

URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"
OUT = ROOT / "backend/exercise_catalog/data/staging/free_exercise_db.json"


def _plain(o):
    if dataclasses.is_dataclass(o):
        return {f.name: _plain(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, (list, tuple)):
        return [_plain(x) for x in o]
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, date):
        return o.isoformat()
    return o


def main(argv):
    raw = Path(argv[1]).read_bytes() if len(argv) > 1 else urllib.request.urlopen(URL, timeout=60).read()
    digest = hashlib.sha256(raw).hexdigest()
    rows = json.loads(raw.decode("utf-8"))
    rep = import_free_exercise_db(rows, source_ref=f"{URL}@sha256:{digest[:16]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps([_plain(r) for r in rep.accepted], ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    manifest = {"source": "yuhonas/free-exercise-db", "url": URL, "retrieved": date.today().isoformat(), "sha256": digest, "upstream_commit": "not pinned (GitHub API unavailable in the build sandbox); content pinned by sha256",
                "input_rows": len(rows), "accepted": len(rep.accepted), "rejected": rep.rejected, "duplicates": rep.duplicates,
                "licence_findings": "Declared Unlicense/public domain by maintainers; no LICENSE file located; image licences not stated; upstream origin unverified -> UNVERIFIED",
                "status": "staging only: pending_review, never loaded into the catalogue, images not referenced"}
    OUT.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"accepted={len(rep.accepted)} rejected={len(rep.rejected)} duplicates={len(rep.duplicates)} sha256={digest[:16]}")


if __name__ == "__main__":
    main(sys.argv)

"""The ingested third-party dataset is staging-only: structurally valid, never publishable, never in the loadable catalogue."""
import json
import pathlib

from exercise_catalog import load_starter, publication_blockers, served_media
from exercise_catalog.loader import _rec

STAGING = pathlib.Path(__file__).resolve().parents[1] / "data" / "staging"


def _rows():
    return [_rec(x) for x in json.loads((STAGING / "free_exercise_db.json").read_text(encoding="utf-8"))]


def test_staging_is_substantial_and_structurally_valid():
    from exercise_catalog import validate_record
    rows = _rows()
    assert len(rows) >= 800
    assert not {r.id: validate_record(r) for r in rows if validate_record(r)}
    assert len({r.id for r in rows}) == len(rows)


def test_no_staged_record_is_publishable_or_published():
    for r in _rows():
        assert r.publication_status == "pending_review"
        assert r.license_status == "third_party_unverified"
        assert r.expert_review == "pending"
        assert publication_blockers(r), r.id
        assert served_media(r) == ()          # images are not even referenced


def test_staging_never_enters_default_catalogue():
    ids = {r.id for r in load_starter()}
    assert len(ids) == 30
    assert not any(i.startswith("fedb_") for i in ids)


def test_manifest_records_provenance_honestly():
    m = json.loads((STAGING / "free_exercise_db.manifest.json").read_text(encoding="utf-8"))
    assert len(m["sha256"]) == 64 and m["accepted"] == len(_rows())
    assert "UNVERIFIED" in m["licence_findings"]


def test_no_machine_translated_persian_names():
    assert all(r.name_fa is None for r in _rows())


def test_media_without_verified_licence_is_not_served():
    from exercise_catalog.schema import ExerciseRecord, MediaRef
    r = ExerciseRecord(id="x", name_en="X", media=(MediaRef("image", "u"), MediaRef("image", "v", "CC0-1.0", True)))
    assert [m.url for m in served_media(r)] == ["v"]

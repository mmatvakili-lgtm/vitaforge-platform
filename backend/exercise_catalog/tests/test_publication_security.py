"""Negative tests: no path (lifecycle service, bridge, loader, importer, admin API, bulk) may publish Experimental / Pending Review content.
Safety/licence status is asserted independently of development/test status."""
import dataclasses
import json
from datetime import date

import pytest

from app_services.catalog import CatalogService
from app_services.errors import ValidationFailed
from app_services.store import InMemoryStore
from devserver.demo_catalog import demo_catalog
from exercise_catalog import SourceRef, import_free_exercise_db, load_starter, publication_blockers, publishable, validate_record
from exercise_catalog import loader
from exercise_catalog.bridge import ProductionCatalogError, assert_production_catalog, to_candidate


def _rec(i="bodyweight_squat"):
    return next(r for r in load_starter() if r.id == i)


def _walk(c, code):
    c.transition("content_admin", "a", code, "scientific_review")
    c.transition("exercise_reviewer", "b", code, "safety_review")


@pytest.mark.parametrize("patch", [dict(),                                                       # experimental starter record as-is
    dict(is_sample=False),                                                                       # not sample but unreviewed
    dict(is_sample=False, expert_review="approved"),                                             # approved but tags unreviewed
    dict(is_sample=False, expert_review="approved", safety_tags_status="reviewed"),              # no sources/date
    dict(is_sample=False, expert_review="approved", safety_tags_status="reviewed", last_reviewed=date(2026, 1, 1)),   # no sources
    dict(is_sample=False, expert_review="approved", safety_tags_status="reviewed", last_reviewed=date(2026, 1, 1),
         evidence_level="guideline", sources=(SourceRef("x", "r", True),)),                      # open review_notes remain
    dict(is_sample=False, expert_review="approved", safety_tags_status="reviewed", last_reviewed=date(2026, 1, 1),
         evidence_level="guideline", sources=(SourceRef("x", "r", True),), review_notes=(), license_status="third_party_unverified")])
def test_lifecycle_refuses_incomplete_record_even_with_full_role_chain(patch):
    s = InMemoryStore(); c = CatalogService(s); ex = demo_catalog()["demo_squat_a"]
    c.create_draft("content_admin", "x", lambda: ex, record=dataclasses.replace(_rec(), **patch), tags_complete=True)
    _walk(c, "x")
    with pytest.raises(ValidationFailed):
        c.transition("clinical_safety_reviewer", "u", "x", "published", tags_complete=True)
    assert "x" not in c.list_public() and s.exercise_meta["x"]["status"] == "safety_review"


def test_lifecycle_refuses_publish_without_any_record():
    s = InMemoryStore(); c = CatalogService(s); ex = demo_catalog()["demo_squat_a"]
    c.create_draft("content_admin", "x", lambda: ex, tags_complete=True)
    _walk(c, "x")
    with pytest.raises(ValidationFailed) as e:
        c.transition("clinical_safety_reviewer", "u", "x", "published", tags_complete=True)
    assert "no_exercise_record" in str(e.value.detail if hasattr(e.value, "detail") else e.value)


def test_bridge_never_marks_claimed_published_as_published_when_blocked():
    r = dataclasses.replace(_rec(), publication_status="published")            # claims published, but is sample/unreviewed
    assert "published but blocked" in " ".join(validate_record(r))
    c = to_candidate(r)
    assert c.review_status != "published" and not c.safety_tags_complete


def test_reviewed_tags_without_approved_expert_review_are_not_complete():
    r = dataclasses.replace(_rec(), safety_tags_status="reviewed", expert_review="pending")
    assert not to_candidate(r).safety_tags_complete


def test_dev_bridge_never_promotes_missing_tags():
    for r in load_starter():
        if r.safety_tags_status == "missing":
            assert not to_candidate(r, dev_experimental=True).safety_tags_complete


def test_loader_rejects_batch_file_claiming_published(tmp_path):
    d = json.loads((loader.DATA).read_text(encoding="utf-8"))[:1]
    d[0]["publication_status"] = "published"
    f = tmp_path / "evil.json"; f.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError):
        loader.load_batches([f])


def test_importer_never_publishes_even_if_row_claims_it():
    rep = import_free_exercise_db([{"id": "x", "name": "X", "equipment": "body only", "primaryMuscles": ["chest"], "level": "beginner",
                                     "publication_status": "published", "expert_review": "approved", "safety_tags_status": "reviewed"}])
    assert rep.accepted
    for r in rep.accepted:
        assert r.publication_status == "pending_review" and r.expert_review == "pending" and r.safety_tags_status == "missing"
        assert r.license_status == "third_party_unverified" and publication_blockers(r)


def test_no_bundled_record_is_publishable_and_production_guard_rejects_them():
    rows = load_starter()
    assert publishable(rows) == []
    assert all(r.publication_status != "published" for r in rows)
    with pytest.raises(ProductionCatalogError):
        assert_production_catalog(rows)


def test_safety_and_licence_status_are_independent_of_development_status():
    """Being 'implemented/tested' (or dev-usable) must not change safety/licence fields."""
    for r in load_starter():
        c = to_candidate(r, dev_experimental=True)
        assert r.expert_review == "pending" and r.license_status == "project_authored"      # unchanged by dev usage
        assert r.safety_tags_status in ("missing", "unreviewed_estimate")
        assert c.review_status == "published"                                              # local-demo shortcut ONLY ...
        assert not to_candidate(r).safety_tags_complete and to_candidate(r).review_status != "published"      # ... never in the default (production) path


def test_dev_shortcut_is_forbidden_in_production_env(monkeypatch):
    monkeypatch.setenv("VITAFORGE_ENV", "production")
    with pytest.raises(ProductionCatalogError):
        to_candidate(_rec(), dev_experimental=True)

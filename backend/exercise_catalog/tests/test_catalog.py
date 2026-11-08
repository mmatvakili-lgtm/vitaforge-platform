from exercise_catalog import loader
import dataclasses
from datetime import date
import pytest
from exercise_catalog import (ExerciseRecord, SourceRef, import_free_exercise_db, load_starter, publication_blockers, publishable,
                              relations, to_candidate, to_catalog_entry, validate_record)
from exercise_catalog.sources import SOURCES
from safety_core import SafetyCore
from safety_core.models import REGIONS, RuleSet, SafetyRequest
from workout_engine import EngineInput, generate_plan

Q = ("chest_pain",)


def test_starter_set_valid_and_honestly_labelled():
    rows = load_starter()
    assert len(rows) >= 25 and len({r.id for r in rows}) == len(rows)
    for r in rows:
        assert validate_record(r) == []
        assert (set(r.region_loads) == set(REGIONS) and r.safety_tags_status == "unreviewed_estimate") or (r.region_loads == {} and r.safety_tags_status == "missing")
        assert r.license_status == "project_authored" and r.review_notes
        assert r.is_sample and r.publication_status == "experimental" and r.expert_review == "pending"
        assert r.evidence_level == "none" and r.last_reviewed is None
        assert r.name_fa and r.instructions and r.primary_muscles
        assert all(a in {x.id for x in rows} for a in r.alternatives + r.regressions)
    assert publishable(rows) == []                      # nothing in the starter set may be published


def test_publication_blockers_listed_and_cleared_only_when_complete():
    r = _starter("bodyweight_squat")
    b = publication_blockers(r)
    assert "sample content" in b and "expert review not approved" in b and "safety tags not reviewed" in b and "no review date" in b
    full = dataclasses.replace(r, is_sample=False, expert_review="approved", safety_tags_status="reviewed", last_reviewed=date(2026, 1, 1),
                               evidence_level="guideline", sources=(SourceRef("x", "ref", True),), review_notes=())
    assert publication_blockers(full) == []
    assert "source license not confirmed for commercial use" in publication_blockers(dataclasses.replace(full, sources=(SourceRef("x", "r", None),)))
    assert "no source" in publication_blockers(dataclasses.replace(full, sources=(), evidence_level="none"))


@pytest.mark.parametrize("patch,issue", [(dict(difficulty="x"), "difficulty"), (dict(movement_pattern="x"), "movement_pattern"),
                                         (dict(evidence_level="guideline"), "evidence_level without sources"), (dict(region_loads={"knee": "bad"}), "region_loads values"),
                                         (dict(publication_status="x"), "publication_status"), (dict(name_en=""), "id/name_en required"),
                                         (dict(region_loads={"knee": "low"}, safety_tags_status="reviewed"), "region_loads must cover all regions")])
def test_validate_catches(patch, issue):
    r = dataclasses.replace(ExerciseRecord(id="a", name_en="A"), **patch)
    assert issue in validate_record(r)


FEDB = [{"id": "Air_Squat", "name": "Air Squat", "force": None, "level": "expert", "mechanic": None, "equipment": "body only",
         "primaryMuscles": ["quadriceps"], "secondaryMuscles": ["glutes"], "instructions": ["Stand.", "Squat."], "category": "strength", "images": ["x.jpg"]},
        {"id": "Air_Squat", "name": "dup"}, {"name": "Band Pull", "level": "beginner", "equipment": "bands", "category": "stretching",
                                              "primaryMuscles": ["shoulders"], "instructions": []}, {"id": "bad"}, "notadict"]


def test_importer_never_publishes_and_reports():
    rep = import_free_exercise_db(FEDB)
    assert [r.id for r in rep.accepted] == ["fedb_air_squat", "fedb_band_pull"] and rep.duplicates == ["fedb_air_squat"]
    assert len(rep.rejected) == 2
    a = rep.accepted[0]
    assert a.publication_status == "pending_review" and a.expert_review == "pending" and a.safety_tags_status == "missing"
    assert a.difficulty == "advanced" and a.equipment == ("bodyweight",) and a.sources[0].license_ok_for_commercial is None
    assert publication_blockers(a) and rep.accepted[1].exercise_type == "stretching"
    assert import_free_exercise_db(FEDB, existing_ids=["fedb_air_squat"]).duplicates.count("fedb_air_squat") == 2


def test_sources_registry_has_no_unverified_claims_marked_true():
    assert SOURCES["wger"].commercial_use is None and SOURCES["free_exercise_db"].commercial_use is None
    assert "Not imported" in SOURCES["wger"].decision


def _starter(i):
    return next(r for r in load_starter() if r.id == i)


def test_production_bridge_blocks_everything_and_dev_allows_for_demo():
    rows = load_starter()
    prod = [to_candidate(r) for r in rows]
    assert all(c.review_status != "published" and not c.safety_tags_complete for c in prod)
    gate = SafetyCore(RuleSet(version=1, status="t", screening_questions=Q, allow_unreviewed_content=True))
    base = SafetyRequest("u", 30, True, {"chest_pain": False})
    inp = EngineInput("u", "general_fitness", "beginner", 3, 90, (), tuple(to_catalog_entry(r) for r in rows))
    r0 = generate_plan(inp, base, gate)                                          # production behaviour: no reviewed content => no plan
    assert r0.status == "BLOCKED" and not r0.days and "SAFETY:RESTRICT" in r0.reasons and "SAF-R015" in r0.reasons
    dev = EngineInput("u", "general_fitness", "beginner", 3, 90, ("dumbbell", "bench", "band", "box"), tuple(to_catalog_entry(r, True) for r in rows))
    res = generate_plan(dev, base, gate)
    assert res.status == "OK" and res.label == "experimental"


def test_relations_and_unknown_region_assumed_high():
    rows = load_starter()
    rel = relations(rows)
    assert ("goblet_squat", "alternative") in rel["bodyweight_squat"]
    r = dataclasses.replace(_starter("bodyweight_squat"), region_loads={})
    assert all(rl.loading == "high" for rl in to_candidate(r, True).region_loads)


def test_production_startup_guard():
    from exercise_catalog.bridge import ProductionCatalogError, assert_production_catalog
    with pytest.raises(ProductionCatalogError):
        assert_production_catalog(load_starter())
    assert_production_catalog([])


def test_bodyweight_pull_batch_is_complete_but_unpublishable():
    rows = {r.id: r for r in load_starter()}
    new = [r for r in rows.values() if r.id.startswith("prone_") or r.id == "reverse_snow_angel"]
    assert len(new) == 5
    for r in new:
        assert r.equipment == () and r.primary_muscles and r.instructions and r.common_mistakes and r.limitations and r.cautions == ()
        assert r.publication_status == "experimental" and r.expert_review == "pending" and r.safety_tags_status == "missing"
        assert r.region_loads == {} and r.evidence_level == "none" and r.license_status == "project_authored"
        b = publication_blockers(r)
        for k in ("sample content", "expert review not approved", "safety tags not reviewed", "no review date", "open review notes"):
            assert k in b, (r.id, k)
    pulls = [r for r in rows.values() if r.push_pull == "pull" and not r.equipment]
    assert len(pulls) >= 4                                  # was 0 before this batch


def test_duplicate_ids_across_batches_rejected(tmp_path):
    import json
    one = json.loads((loader.DATA).read_text(encoding="utf-8"))[:1]
    (tmp_path / "a.json").write_text(json.dumps(one), encoding="utf-8")
    assert len(load_starter(tmp_path / "a.json")) == 1
    with pytest.raises(ValueError):
        loader.load_batches([tmp_path / "a.json", tmp_path / "a.json"])


@pytest.mark.parametrize("patch,issue", [(dict(license_status="x"), "license_status"),
        (dict(safety_tags_status="missing", region_loads={"knee": "low"}), "region_loads present but safety_tags_status is 'missing' (label estimates 'unreviewed_estimate')"),
        (dict(safety_tags_status="reviewed", expert_review="pending"), "safety tags marked reviewed without approved expert review"),
        (dict(equipment=("bodyweight", "band")), "bodyweight cannot be combined with other equipment"),
        (dict(publication_status="published"), None)])
def test_new_invariants(patch, issue):
    r = dataclasses.replace(_starter("bodyweight_squat"), **patch)
    v = validate_record(r)
    if issue: assert issue in v
    else: assert any(x.startswith("published but blocked") for x in v)       # cannot be Published while blockers exist


def test_unverified_license_and_vocab_block_publication():
    r = dataclasses.replace(_starter("bodyweight_squat"), is_sample=False, expert_review="approved", safety_tags_status="reviewed", last_reviewed=date(2026, 1, 1),
                            evidence_level="guideline", sources=(SourceRef("x", "ref", True),), review_notes=())
    assert publication_blockers(r) == []
    assert "license status not confirmed" in publication_blockers(dataclasses.replace(r, license_status="third_party_unverified"))
    assert "muscle names outside controlled vocabulary" in publication_blockers(dataclasses.replace(r, primary_muscles=("quads",)))
    assert "equipment outside controlled vocabulary" in publication_blockers(dataclasses.replace(r, equipment=("sofa",)))


def test_coded_cautions_must_be_pairs():
    r = dataclasses.replace(_starter("bodyweight_squat"), cautions=("free text",))
    assert "cautions/contraindications must be (code, region) pairs" in validate_record(r)


def test_missing_safety_tags_block_even_in_dev_bridge_and_unknown_load_is_high():
    r = _starter("prone_y_raise")
    c = to_candidate(r, dev_experimental=True)
    assert not c.safety_tags_complete                       # 'missing' is never promoted, even for dev demos
    assert all(rl.loading == "high" for rl in c.region_loads)

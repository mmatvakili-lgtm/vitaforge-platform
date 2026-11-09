import pytest
from app_services.catalog import CatalogService
from app_services.errors import FeatureUnavailable, Forbidden, NotFound, ValidationFailed
from app_services.store import InMemoryStore
from app_services.subscriptions import DisabledPaymentProvider, SubscriptionService
from devserver.demo_catalog import demo_catalog


def _approved_fixture():
    import dataclasses
    from datetime import date
    from exercise_catalog import SourceRef, load_starter
    base = next(r for r in load_starter() if r.id == "bodyweight_squat")
    return dataclasses.replace(base, is_sample=False, expert_review="approved", safety_tags_status="reviewed", last_reviewed=date(2026, 1, 1),
                               evidence_level="guideline", sources=(SourceRef("x", "ref", True),), review_notes=())


def cat():
    s = InMemoryStore()
    return s, CatalogService(s)


def test_full_lifecycle_and_roles():
    s, c = cat()
    ex = demo_catalog()["demo_squat_a"]
    c.create_draft("content_admin", "x1", lambda: ex, record=_approved_fixture())     # TEST FIXTURE only: stands in for a future real sign-off
    with pytest.raises(NotFound):
        c.get_public("x1")
    c.transition("content_admin", "u1", "x1", "scientific_review")
    c.transition("exercise_reviewer", "u2", "x1", "safety_review")
    assert "x1" not in c.list_public()
    c.transition("clinical_safety_reviewer", "u3", "x1", "published", tags_complete=True)
    assert c.list_public() == ["x1"] and c.coverage_report() == {"squat": 1}
    assert [x["to"] for x in s.exercise_meta["x1"]["signoffs"]] == ["scientific_review", "safety_review", "published"]
    c.transition("clinical_safety_reviewer", "u3", "x1", "retired")
    assert c.list_public() == []                      # AC-EX-003


@pytest.mark.parametrize("role,target", [("admin", "published"), ("content_admin", "published"), ("exercise_reviewer", "scientific_review")])
def test_wrong_role_cannot_advance(role, target):
    s, c = cat(); ex = demo_catalog()["demo_squat_a"]
    c.create_draft("content_admin", "x", lambda: ex)
    c.s.exercise_meta["x"]["status"] = "safety_review" if target == "published" else "draft"
    with pytest.raises(Forbidden):
        c.transition(role, "u", "x", target, tags_complete=True)


def test_skip_steps_incomplete_tags_sample_and_forbidden_create():
    s, c = cat(); ex = demo_catalog()["demo_squat_a"]
    c.create_draft("content_admin", "x", lambda: ex)
    with pytest.raises(ValidationFailed):
        c.transition("clinical_safety_reviewer", "u", "x", "published", tags_complete=True)   # skipped reviews
    with pytest.raises(Forbidden):
        c.create_draft("user", "y", lambda: ex)
    with pytest.raises(ValidationFailed):
        c.create_draft("content_admin", "x", lambda: ex)
    with pytest.raises(NotFound):
        c.transition("admin", "u", "nope", "retired")
    c.create_draft("content_admin", "smp", lambda: ex, sample=True)
    for r, t in [("content_admin", "scientific_review"), ("exercise_reviewer", "safety_review")]:
        c.transition(r, "u", "smp", t)
    with pytest.raises(ValidationFailed):
        c.transition("clinical_safety_reviewer", "u", "smp", "published", tags_complete=True)  # SAMPLE never published
    c.create_draft("content_admin", "z", lambda: ex)
    for r, t in [("content_admin", "scientific_review"), ("exercise_reviewer", "safety_review")]:
        c.transition(r, "u", "z", t)
    with pytest.raises(ValidationFailed):
        c.transition("clinical_safety_reviewer", "u", "z", "published", tags_complete=False)


def test_rule_set_publish_needs_expert_ref():
    s, c = cat()
    with pytest.raises(Forbidden):
        c.publish_rule_set("admin", "u", 2, "EXP-001")
    with pytest.raises(ValidationFailed):
        c.publish_rule_set("clinical_safety_reviewer", "u", 2, "  ")
    assert c.publish_rule_set("clinical_safety_reviewer", "u", 2, "EXP-001-signed")["status"] == "published"


def subs():
    s = InMemoryStore(); return s, SubscriptionService(s, DisabledPaymentProvider(), {("pro", "ai_chat"): 3})


def test_subscription_flow():
    s, sv = subs()
    assert sv.plans() == ["free", "pro"] and sv.me("u") == {"plan": "free", "active": True}
    with pytest.raises(FeatureUnavailable):
        sv.checkout("u", "pro")                          # payments not configured -> never faked
    with pytest.raises(ValidationFailed):
        sv.checkout("u", "free")
    assert not sv.access("u", "ai_chat").allowed
    sv.activate("u", "pro")
    assert sv.access("u", "ai_chat", used=2).allowed and sv.access("u", "ai_chat", used=3).reason == "quota_exhausted"
    sv.cancel("u")
    assert sv.me("u")["plan"] == "free" and sv.access("u", "safety_screening", used=999).allowed
    with pytest.raises(NotFound):
        sv.cancel("u")


def test_admin_cannot_remove_safety_feature_from_plan():
    s, sv = subs()
    with pytest.raises(Forbidden):
        sv.set_plan_features("user", "free", ["plan_generation"])
    with pytest.raises(ValidationFailed):
        sv.set_plan_features("admin", "free", ["plan_generation"])        # drops safety_screening
    with pytest.raises(ValidationFailed):
        sv.set_plan_features("admin", "free", ["safety_screening", "restrictions", "bogus"])
    sv.set_plan_features("admin", "free", ["safety_screening", "restrictions"])
    assert not sv.access("u", "plan_generation").allowed and sv.access("u", "safety_screening").allowed

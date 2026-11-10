"""Plans built from the experimental starter catalogue must say so; only published records under a non-dev rule set may be labelled published."""
from contract.harness import Harness
from contract import scenarios


def test_dev_content_plan_is_labelled_experimental():
    h = Harness()
    t = h.login("prov@ex.com")
    h.onboard(t)
    h.call("POST", "/onboarding/complete", token=t)
    gen = h.call("POST", "/workouts/generate", {"preferred_structure": "auto"}, token=t).body
    assert gen["plan"] is not None
    assert gen["plan"]["rationale"]["content_status"] == "experimental_unreviewed"
    assert gen["decision"]["status"] in ("ALLOW", "ALLOW_WITH_MODIFICATION")


def test_restrict_never_returns_a_plan():
    from safety_core.models import DecisionStatus
    assert DecisionStatus.RESTRICT.permits_content is False
    assert DecisionStatus.ALLOW.permits_content and DecisionStatus.ALLOW_WITH_MODIFICATION.permits_content


def test_exercise_detail_exposes_review_status_and_no_unlicensed_media():
    h = Harness()
    t = h.login("det@ex.com")
    h.onboard(t)
    eid = h.call("GET", "/exercises?page=1&page_size=1", token=t).body["results"][0]["id"]
    d = h.call("GET", f"/exercises/{eid}", token=t).body
    assert d["review_status"] != "published" and d["media"] == []

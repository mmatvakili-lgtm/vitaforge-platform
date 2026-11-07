import pytest
from entitlements import Feature, PlanCatalog, check_access

F = {"safety": Feature("safety", True), "ai_chat": Feature("ai_chat"), "plan_gen": Feature("plan_gen")}
PF = {"free": frozenset({"safety", "plan_gen"}), "pro": frozenset({"safety", "plan_gen", "ai_chat"})}
Q = {("pro", "ai_chat"): 5}
C = PlanCatalog(F, PF, Q)


def test_safety_always_allowed_even_inactive_or_unknown_plan():
    for plan in ("free", "pro", "ghost"):
        assert check_access(C, plan, "safety", used=10**6, subscription_active=False).reason == "safety_critical"


def test_gating_and_quota():
    assert check_access(C, "free", "ai_chat").reason == "not_in_plan"
    assert check_access(C, "pro", "ai_chat", used=4) == check_access(C, "pro", "ai_chat", used=4) and check_access(C, "pro", "ai_chat", used=4).consume_quota
    assert check_access(C, "pro", "ai_chat", used=5).reason == "quota_exhausted"
    assert check_access(C, "free", "plan_gen").allowed and not check_access(C, "free", "plan_gen").consume_quota


def test_inactive_and_unknown():
    assert check_access(C, "pro", "ai_chat", subscription_active=False).reason == "subscription_inactive"
    assert check_access(C, "free", "plan_gen", subscription_active=False).allowed
    assert check_access(C, "pro", "nope").reason == "unknown_feature"


def test_catalog_invariants():
    with pytest.raises(ValueError):
        PlanCatalog(F, {"free": frozenset({"plan_gen"})})
    with pytest.raises(ValueError):
        PlanCatalog(F, PF, {("pro", "safety"): 3})

"""Plans, checkout (PaymentProvider port) and cancellation. Safety features are never gated (ADR-0003)."""
from __future__ import annotations

from typing import Protocol

from entitlements import Feature, PlanCatalog, check_access

from .errors import Forbidden, NotFound, PreconditionRequired, ValidationFailed

FEATURES = {"safety_screening": Feature("safety_screening", True), "restrictions": Feature("restrictions", True),
            "plan_generation": Feature("plan_generation"), "workout_logging": Feature("workout_logging"),
            "ai_chat": Feature("ai_chat")}
DEFAULT_PLAN_FEATURES = {"free": frozenset({"safety_screening", "restrictions", "plan_generation", "workout_logging"}),
                         "pro": frozenset(FEATURES)}


class PaymentProvider(Protocol):
    code: str
    def create_checkout(self, user_id: str, plan: str) -> dict: ...


class DisabledPaymentProvider:
    """Default until OPEN-001/005 are decided: checkout is explicitly unavailable, never faked."""
    code = "disabled"

    def create_checkout(self, user_id, plan):
        raise PreconditionRequired("payments_not_configured")


class SubscriptionService:
    def __init__(self, store, payments: PaymentProvider, quotas=None):
        self.s, self.pay = store, payments
        self.catalog = PlanCatalog(FEATURES, dict(DEFAULT_PLAN_FEATURES), quotas or {})        # quotas are configuration (OPEN-005)
        self.s.__dict__.setdefault("subs", {})

    def plans(self):
        return sorted(self.catalog.plan_features)

    def me(self, uid):
        return self.s.subs.get(uid, {"plan": "free", "active": True})

    def checkout(self, uid, plan):
        if plan not in self.catalog.plan_features or plan == "free":
            raise ValidationFailed("plan")
        return self.pay.create_checkout(uid, plan)

    def activate(self, uid, plan):                      # called by a verified payment webhook only
        self.s.subs[uid] = {"plan": plan, "active": True}

    def cancel(self, uid):
        cur = self.s.subs.get(uid)
        if not cur or cur["plan"] == "free":
            raise NotFound()
        self.s.subs[uid] = {"plan": "free", "active": True}     # safety features remain; data untouched

    def access(self, uid, feature, used=0):
        sub = self.me(uid)
        return check_access(self.catalog, sub["plan"], feature, used, sub["active"])

    def set_plan_features(self, actor_role, plan, features):
        if actor_role != "admin":
            raise Forbidden()
        feats = frozenset(features)
        unknown = feats - set(FEATURES)
        if unknown:
            raise ValidationFailed("unknown_features")
        new = dict(self.catalog.plan_features); new[plan] = feats
        try:
            self.catalog = PlanCatalog(FEATURES, new, self.catalog.quotas)   # invariant: safety_critical in every plan
        except ValueError as e:
            raise ValidationFailed(str(e))

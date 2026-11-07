"""Entitlement logic (FR-SUB-003): safety_critical features are never gated by plan or quota."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional


@dataclass(frozen=True)
class Feature:
    code: str
    safety_critical: bool = False


@dataclass(frozen=True)
class PlanCatalog:
    features: Mapping[str, Feature]
    plan_features: Mapping[str, frozenset]            # plan -> feature codes
    quotas: Mapping[tuple, Optional[int]] = field(default_factory=dict)   # (plan, feature) -> limit; None = unlimited

    def __post_init__(self):
        # Structural invariant: a safety-critical feature must be in EVERY plan.
        for f in self.features.values():
            if f.safety_critical:
                for plan, feats in self.plan_features.items():
                    if f.code not in feats:
                        raise ValueError(f"safety_critical feature {f.code} missing from plan {plan}")
                for (plan, code), lim in self.quotas.items():
                    if code == f.code and lim is not None:
                        raise ValueError(f"safety_critical feature {f.code} must not have a quota")


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str                 # ok | safety_critical | not_in_plan | quota_exhausted | unknown_feature | subscription_inactive
    consume_quota: bool = False


def check_access(catalog: PlanCatalog, plan: str, feature_code: str, used: int = 0, subscription_active: bool = True) -> AccessDecision:
    f = catalog.features.get(feature_code)
    if f is None:
        return AccessDecision(False, "unknown_feature")
    if f.safety_critical:
        return AccessDecision(True, "safety_critical")      # independent of plan, quota, payment state
    if not subscription_active and plan != "free":
        return AccessDecision(False, "subscription_inactive")
    if feature_code not in catalog.plan_features.get(plan, frozenset()):
        return AccessDecision(False, "not_in_plan")
    limit = catalog.quotas.get((plan, feature_code))
    if limit is not None and used >= limit:
        return AccessDecision(False, "quota_exhausted")
    return AccessDecision(True, "ok", consume_quota=limit is not None)

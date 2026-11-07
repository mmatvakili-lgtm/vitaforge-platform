"""AI Gateway pipeline (DOC-08 §2). Safety first, LLM optional, fixed fallbacks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from safety_core.models import SafetyDecision

from .errors import PolicyViolation
from .policy import build_context, classify_intent, contains_health_text, redact_text
from .ports import LLMProvider, ModelRequest, ProviderUnavailable
from .validator import validate_output

FIXED = {
    "out_of_scope": "این پرسش در حوزه این برنامه نیست. برای تشخیص، درمان یا دوز دارو با پزشک یا متخصص مشورت کنید.",
    "safety": "بر اساس ارزیابی ایمنی، فعلاً برنامه یا توضیح ارائه نمی‌شود. لطفاً با متخصص مشورت کنید.",
    "health_text": "برای حفظ حریم خصوصی، اطلاعات سلامت را در این گفتگو وارد نکنید.",
    "fallback": "توضیح خودکار در دسترس نیست؛ برنامه شما همچنان معتبر است.",
    "quota": "سهمیه پیام‌های هوشمند شما به پایان رسیده است.",
}


@dataclass(frozen=True)
class GatewayResult:
    mode: str                         # ai | fixed | rule_based_fallback
    text: str
    reason: str
    exercises: Tuple[str, ...] = ()
    uncertainty: Optional[str] = None
    safety_decision_id: Optional[str] = None
    consumed_quota: bool = False


class AIGateway:
    def __init__(self, provider: LLMProvider, prompt_id: str = "explain_plan", prompt_version: int = 1,
                 prompt_approved: bool = True, external_health_data: bool = False, llm_enabled: bool = True):
        if external_health_data:
            raise PolicyViolation("external_health_data must stay disabled until legal review (EXP-012)")
        self.provider, self.prompt_id, self.prompt_version = provider, prompt_id, prompt_version
        self.prompt_approved, self.llm_enabled = prompt_approved, llm_enabled

    def respond(self, user_text: str, source_context: Mapping[str, Any], decision: SafetyDecision,
                allowed_codes, quota_remaining: Optional[int] = None, source_ids=()) -> GatewayResult:
        did = decision.decision_id
        # 3-4 safety first: never consumes quota, never calls the LLM
        if not decision.status.permits_content:
            return GatewayResult("fixed", FIXED["safety"], "safety:" + decision.status.value, safety_decision_id=did)
        intent = classify_intent(user_text)                                           # 1
        if intent == "unsafe_medical":
            return GatewayResult("fixed", FIXED["out_of_scope"], "intent:unsafe_medical", safety_decision_id=did)
        if contains_health_text(user_text):
            return GatewayResult("fixed", FIXED["health_text"], "health-text", safety_decision_id=did)
        if not self.llm_enabled or not self.prompt_approved:
            return GatewayResult("rule_based_fallback", FIXED["fallback"], "llm-disabled", safety_decision_id=did)
        if quota_remaining is not None and quota_remaining <= 0:
            return GatewayResult("fixed", FIXED["quota"], "quota", safety_decision_id=did)
        ctx = build_context(intent, source_context)                                  # 2
        req = ModelRequest(self.prompt_id, self.prompt_version, redact_text(user_text), ctx, data_class="non_health")
        if getattr(self.provider, "external", False) and req.data_class != "non_health":
            raise PolicyViolation("health data to external provider")                # AC-AI-002
        try:
            resp = self.provider.generate(req)                                       # 7
        except ProviderUnavailable:
            return GatewayResult("rule_based_fallback", FIXED["fallback"], "provider-down", safety_decision_id=did)
        v = validate_output(resp.payload, allowed_codes, source_ids)                 # 8
        if not v.ok:
            return GatewayResult("rule_based_fallback", FIXED["fallback"], "validator:" + ",".join(v.reasons),
                                 safety_decision_id=did)
        p = resp.payload
        return GatewayResult("ai", p["text"], "ok", tuple(p["exercises"]), p["uncertainty"], did, consumed_quota=True)

"""AI Decision Layer: User Context -> Rule Engine -> Retrieval -> AI Generation -> Output Validation -> Safety Validation -> Response.

The rule engine answers whenever a deterministic, safe answer exists; the LLM is only used for what rules cannot say, and only with
retrieved, published sources. Every response carries a stage trace so the decision is explainable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Protocol, Tuple

from safety_core.models import SafetyDecision

from .gateway import FIXED, AIGateway
from .policy import classify_intent, contains_health_text, redact_text
from .ports import ModelRequest, ProviderUnavailable
from .validator import validate_output

NEXT_SESSION = re.compile(r"next (workout|session)|جلسه (بعد|بعدی)|تمرین (بعد|بعدی)", re.I)
WHY_PLAN = re.compile(r"why|چرا|توضیح|explain", re.I)
NUTRITION = re.compile(r"calorie|tdee|bmr|protein|کالری|پروتئین|انرژی", re.I)
TECHNIQUE = re.compile(r"technique|form|how (to|do)|فرم|تکنیک|چطور", re.I)


@dataclass(frozen=True)
class Chunk:
    source_id: str
    text: str
    status: str                 # published | experimental
    exercise_code: Optional[str] = None


class KnowledgeBase(Protocol):
    def retrieve(self, query: str, exercise_codes: Tuple[str, ...]) -> List[Chunk]: ...


class EmptyKnowledgeBase:
    def retrieve(self, query, exercise_codes):
        return []


class ExerciseKnowledgeBase:
    """Retrieval over exercise instructions. Only `published` chunks are returned unless allow_experimental (dev, labelled)."""

    def __init__(self, records, allow_experimental: bool = False):
        self.records, self.allow = list(records), allow_experimental

    def retrieve(self, query, exercise_codes):
        out = []
        for r in self.records:
            if exercise_codes and r.id not in exercise_codes:
                continue
            if r.publication_status != "published" and not (self.allow and r.publication_status == "experimental"):
                continue
            if r.instructions and (r.id.replace("_", " ") in query.lower() or r.name_en.lower() in query.lower()
                                   or (r.name_fa and r.name_fa in query)):
                out.append(Chunk(r.id, " ".join(r.instructions), r.publication_status, r.id))
        return out


@dataclass(frozen=True)
class DecisionResponse:
    mode: str                                   # rule | ai | fixed | fallback | uncertain
    text: str
    trace: Tuple[Tuple[str, str], ...]
    uncertainty: str = "high"
    sources: Tuple[str, ...] = ()
    labels: Tuple[str, ...] = ()
    safety_decision_id: Optional[str] = None
    consumed_quota: bool = False


class DecisionLayer:
    def __init__(self, gateway: AIGateway, kb: KnowledgeBase = EmptyKnowledgeBase(), lang: str = "fa"):
        self.gw, self.kb, self.lang = gateway, kb, lang

    def respond(self, text: str, decision: SafetyDecision, plan=None, nutrition=None, quota_remaining: Optional[int] = None) -> DecisionResponse:
        tr: List[Tuple[str, str]] = [("context", "plan" if plan else "no-plan")]
        did = decision.decision_id
        # --- safety first (deterministic; never LLM)
        if not decision.status.permits_content:
            tr.append(("safety", decision.status.value))
            return DecisionResponse("fixed", FIXED["safety"], tuple(tr), "high", (), (), did)
        tr.append(("safety", "permits"))
        if classify_intent(text) == "unsafe_medical":
            tr.append(("rule_engine", "refuse:medical"))
            return DecisionResponse("fixed", FIXED["out_of_scope"], tuple(tr), "high", (), (), did)
        if contains_health_text(text):
            tr.append(("rule_engine", "refuse:health-text"))
            return DecisionResponse("fixed", FIXED["health_text"], tuple(tr), "high", (), (), did)
        # --- rule engine: deterministic answers
        ruled = self._rules(text, plan, nutrition)
        if ruled:
            tr.append(("rule_engine", "answered"))
            return DecisionResponse("rule", ruled[0], tuple(tr), ruled[1], (), ("rule_based",), did)
        tr.append(("rule_engine", "no-answer"))
        # --- retrieval
        codes = tuple(plan.codes) if plan else ()
        chunks = self.kb.retrieve(text, codes) if TECHNIQUE.search(text) or WHY_PLAN.search(text) else []
        tr.append(("retrieval", f"{len(chunks)}-chunks"))
        if TECHNIQUE.search(text) and not chunks:
            tr.append(("uncertainty", "no-verified-source"))
            msg = "اطلاعات تأییدشده‌ای برای این حرکت در دسترس نیست؛ برای فرم صحیح از مربی یا منبع معتبر کمک بگیر." if self.lang == "fa" \
                else "No verified information is available for this movement; please consult a coach or a reliable source."
            return DecisionResponse("uncertain", msg, tuple(tr), "high", (), (), did)
        # --- generation (optional, only where rules cannot answer)
        r = self.gw.respond(text, {"structure": getattr(plan, "structure", None), "exercise_names": list(codes)}, decision, codes,
                            quota_remaining=quota_remaining, source_ids=[c.source_id for c in chunks])
        tr.append(("generation", r.reason))
        if r.mode != "ai":
            tr.append(("output_validation", "n/a"))
            mode = "fixed" if r.mode == "fixed" else "fallback"
            return DecisionResponse(mode, r.text, tuple(tr), "high", (), (), did)
        tr.append(("output_validation", "ok"))
        # --- safety validation of the generated output (second, independent check)
        if not set(r.exercises) <= set(codes):
            tr.append(("safety_validation", "rejected:foreign-exercise"))
            return DecisionResponse("fallback", FIXED["fallback"], tuple(tr), "high", (), (), did)
        tr.append(("safety_validation", "ok"))
        labels = tuple(sorted({"experimental_source" if c.status != "published" else "published_source" for c in chunks})) or ("no_sources",)
        return DecisionResponse("ai", r.text, tuple(tr), r.uncertainty or "high", tuple(c.source_id for c in chunks), labels, did, r.consumed_quota)

    def _rules(self, text, plan, nutrition) -> Optional[Tuple[str, str]]:
        fa = self.lang == "fa"
        if plan is not None and NEXT_SESSION.search(text):
            d = plan.days[0]
            ex = "، ".join(e.code for e in d.exercises)
            return (f"جلسه بعدی: {d.name} — {ex}." if fa else f"Next session: {d.name} — {ex}."), "low"
        if plan is not None and WHY_PLAN.search(text) and not TECHNIQUE.search(text):
            parts = [f"structure={plan.structure}", f"confidence={plan.confidence}"] + list(plan.reasons)
            if plan.omissions:
                parts.append(f"omissions={len(plan.omissions)}")
            head = "دلیل ساخت این برنامه (قاعده‌محور و تجربی): " if fa else "Why this plan (rule-based, experimental): "
            return head + "; ".join(parts), "medium"
        if nutrition is not None and NUTRITION.search(text):
            if nutrition.status != "OK":
                return (("برای تخمین تغذیه به اطلاعات بیشتر یا ارزیابی تخصصی نیاز است." if fa else "More information or a professional assessment is needed."), "high")
            t = nutrition.tdee
            return ((f"تخمین انرژی مصرفی روزانه بین {t[0]} و {t[2]} کیلوکالری (تقریبی، بدون تأیید تخصصی)." if fa
                     else f"Estimated daily energy use is {t[0]}–{t[2]} kcal (approximate, not expert reviewed)."), nutrition.uncertainty)
        return None

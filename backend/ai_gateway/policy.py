"""Intent routing, purpose-based context building and PII/health redaction (DOC-08 §3, §6)."""
from __future__ import annotations

import re
from typing import Any, Mapping

# Fields that can NEVER leave the trust boundary, whatever the purpose says.
NEVER_SEND = frozenset({"pain", "pain_log", "diagnosis", "conditions", "restrictions", "birth_date", "name", "email",
                        "phone", "health", "medications", "injury", "weight_kg", "body_measurements", "red_flag_answers"})

PURPOSE_WHITELIST = {
    "explain_plan": frozenset({"structure", "exercise_names", "reasons", "goal", "level"}),
    "technique": frozenset({"exercise_names"}),
    "general": frozenset(),
}

UNSAFE_PATTERNS = [
    r"diagnos", r"\bdose\b", r"\bdosage\b", r"prescri", r"treat(ment)?\b", r"cure\b", r"rehab",
    "تشخیص", "دوز", "درمان", "داروی", "مکمل.*مصرف", "بازتوانی",
]
_UNSAFE = re.compile("|".join(UNSAFE_PATTERNS), re.I)
_TECHNIQUE = re.compile(r"technique|form|how to perform|how do i do|فرم|تکنیک|چطور انجام", re.I)
_EXPLAIN = re.compile(r"why|explain|plan|چرا|توضیح|برنامه", re.I)

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
HEALTH_WORDS = re.compile(r"pain|injur|surgery|fractur|hernia|disc\b|درد|آسیب|جراحی|شکستگی|دیسک|فتق|بیماری", re.I)


def classify_intent(text: str) -> str:
    """Rule-based; no LLM. Unsafe/medical wins over everything else."""
    if _UNSAFE.search(text or ""):
        return "unsafe_medical"
    if _TECHNIQUE.search(text or ""):
        return "technique"
    if _EXPLAIN.search(text or ""):
        return "explain_plan"
    return "general"


def build_context(purpose: str, source: Mapping[str, Any]) -> dict:
    """Whitelist projection. Unknown purpose => empty context (deny by default)."""
    allowed = PURPOSE_WHITELIST.get(purpose, frozenset()) - NEVER_SEND
    return {k: v for k, v in source.items() if k in allowed}


def redact_text(text: str) -> str:
    text = EMAIL.sub("[email]", text or "")
    return PHONE.sub("[phone]", text)


def contains_health_text(text: str) -> bool:
    return bool(HEALTH_WORDS.search(text or ""))

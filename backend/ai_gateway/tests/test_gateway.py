import dataclasses
import random
import string
import pytest
from ai_gateway import (AIGateway, PolicyViolation, StubProvider, build_context, classify_intent, redact_text,
                        validate_output)
from ai_gateway.policy import NEVER_SEND, PURPOSE_WHITELIST
from ai_gateway.ports import ModelRequest
from safety_core import evaluate
from safety_core.models import RuleSet
from safety_core.tests.conftest import QUESTIONS, make_ex
from safety_core.models import SafetyRequest

RS = RuleSet(version=1, status="t", screening_questions=QUESTIONS, allow_unreviewed_content=True)


def dec(**kw):
    d = dict(user_id="u", age_years=30, consent_health_valid=True, red_flag_answers={q: False for q in QUESTIONS},
             candidates=(make_ex("squat"),))
    d.update(kw)
    return evaluate(SafetyRequest(**d), RS)


CTX = {"structure": "full_body", "exercise_names": ["squat"], "pain": "knee", "name": "Ali", "diagnosis": "x"}


def test_external_health_flag_rejected():
    with pytest.raises(PolicyViolation):
        AIGateway(StubProvider(), external_health_data=True)


def test_happy_path_ai():
    r = AIGateway(StubProvider()).respond("why this plan?", CTX, dec(), ["squat"], quota_remaining=3)
    assert r.mode == "ai" and r.consumed_quota and r.exercises == ("squat",)


def test_stub_receives_no_health_context():
    seen = {}

    class Spy(StubProvider):
        def generate(self, req: ModelRequest):
            seen["ctx"], seen["text"] = dict(req.context), req.user_text
            return super().generate(req)
    AIGateway(Spy()).respond("explain plan, mail a@b.com", CTX, dec(), ["squat"])
    assert not set(seen["ctx"]) & NEVER_SEND and "a@b.com" not in seen["text"]


def test_safety_stop_fixed_no_llm_no_quota():
    class Boom(StubProvider):
        def generate(self, req): raise AssertionError("LLM must not be called")
    d = dec(age_years=15)
    r = AIGateway(Boom()).respond("why?", CTX, d, [], quota_remaining=0)
    assert r.mode == "fixed" and not r.consumed_quota and r.reason.startswith("safety:")


@pytest.mark.parametrize("t", ["can you diagnose my knee", "what dose of creatine", "تشخیص بده", "دوز مکمل چقدر است"])
def test_unsafe_intent_fixed(t):
    assert AIGateway(StubProvider()).respond(t, CTX, dec(), ["squat"]).reason == "intent:unsafe_medical"


def test_health_text_blocked():
    assert AIGateway(StubProvider()).respond("why does my knee pain matter in plan", CTX, dec(), ["squat"]).reason == "health-text"


def test_provider_down_fallback_and_safety_unaffected():
    r = AIGateway(StubProvider(fail=True)).respond("explain plan", CTX, dec(), ["squat"])
    assert r.mode == "rule_based_fallback" and r.reason == "provider-down" and not r.consumed_quota


def test_validator_rejects_foreign_exercise():
    gw = AIGateway(StubProvider(payload={"text": "ok", "exercises": ["deadlift"], "claims": [], "uncertainty": "low"}))
    r = gw.respond("explain plan", CTX, dec(), ["squat"])
    assert r.mode == "rule_based_fallback" and "SAF-R009:deadlift" in r.reason


def test_quota_exhausted_and_disabled_and_unapproved_prompt():
    g = AIGateway(StubProvider())
    assert g.respond("explain plan", CTX, dec(), ["squat"], quota_remaining=0).reason == "quota"
    assert AIGateway(StubProvider(), llm_enabled=False).respond("explain plan", CTX, dec(), ["squat"]).reason == "llm-disabled"
    assert AIGateway(StubProvider(), prompt_approved=False).respond("explain plan", CTX, dec(), ["squat"]).reason == "llm-disabled"


@pytest.mark.parametrize("p,ok", [
    ({"text": "fine", "exercises": [], "claims": [], "uncertainty": "low"}, True),
    ({"text": "you have a torn disc", "exercises": [], "claims": [], "uncertainty": "low"}, False),
    ({"text": "take 500 mg daily", "exercises": [], "claims": [], "uncertainty": "low"}, False),
    ({"text": "push through pain", "exercises": [], "claims": [], "uncertainty": "low"}, False),
    ({"text": "با درد ادامه دهید", "exercises": [], "claims": [], "uncertainty": "low"}, False),
    ({"text": "x", "exercises": [], "claims": [{"text": "c"}], "uncertainty": "low"}, False),
    ({"text": "x", "exercises": [], "claims": [{"text": "c", "source_id": "S1"}], "uncertainty": "low"}, True),
    ({"text": "", "exercises": [], "claims": [], "uncertainty": "low"}, False),
    ({"text": "x", "exercises": [], "claims": [], "uncertainty": "sure"}, False),
    ({"text": "x", "exercises": "a", "claims": [], "uncertainty": "low"}, False),
    ({"text": "x", "exercises": [], "claims": {}, "uncertainty": "low"}, False),
    ("string", False)])
def test_validator(p, ok):
    assert validate_output(p, [], ["S1"]).ok is ok


def test_context_whitelist_deny_by_default():
    assert build_context("unknown", CTX) == {}
    assert build_context("explain_plan", CTX) == {"structure": "full_body", "exercise_names": ["squat"]}


def test_property_no_never_send_key_ever_passes():
    rnd = random.Random(7)
    keys = list(NEVER_SEND) + list(string.ascii_lowercase[:6]) + [k for s in PURPOSE_WHITELIST.values() for k in s]
    for _ in range(300):
        src = {rnd.choice(keys): rnd.random() for _ in range(rnd.randint(1, 8))}
        for purpose in list(PURPOSE_WHITELIST) + ["zzz"]:
            assert not set(build_context(purpose, src)) & NEVER_SEND


def test_whitelists_never_contain_forbidden():
    assert all(not (s & NEVER_SEND) for s in PURPOSE_WHITELIST.values())


def test_redact_and_intents():
    assert redact_text("call +98 912 123 4567 or a.b@c.io") == "call [phone] or [email]"
    assert classify_intent("how to perform squat form") == "technique" and classify_intent("hi") == "general"

import dataclasses
import pytest
from ai_gateway import AIGateway, DecisionLayer, EmptyKnowledgeBase, ExerciseKnowledgeBase, StubProvider
from exercise_catalog import load_starter
from nutrition_engine import NutritionProfile, estimate
from nutrition_engine.tests.test_nutrition import BASE, GATE, prof
from safety_core import evaluate
from safety_core.models import RuleSet, SafetyRequest
from safety_core.tests.conftest import QUESTIONS, make_ex
from workout_engine import CatalogExercise, EngineInput, generate_plan
from workout_engine.tests.test_engine import catalog

RS = RuleSet(version=1, status="t", screening_questions=QUESTIONS, allow_unreviewed_content=True)


def decision(**kw):
    d = dict(user_id="u", age_years=30, consent_health_valid=True, red_flag_answers={q: False for q in QUESTIONS}, candidates=(make_ex("x"),))
    d.update(kw)
    return evaluate(SafetyRequest(**d), RS)


@pytest.fixture
def plan():
    from safety_core import SafetyCore
    g = SafetyCore(RS)
    b = SafetyRequest("u", 30, True, {q: False for q in QUESTIONS})
    return generate_plan(EngineInput("u", "muscle_gain", "beginner", 3, 60, (), catalog()), b, g)


def layer(provider=None, kb=None, **kw):
    return DecisionLayer(AIGateway(provider or StubProvider(), **kw), kb or EmptyKnowledgeBase(), "en")


def stages(r):
    return [s for s, _ in r.trace]


def test_rule_engine_answers_without_llm(plan):
    class Boom(StubProvider):
        def generate(self, req): raise AssertionError("LLM must not be called")
    r = layer(Boom()).respond("what is my next session?", decision(), plan)
    assert r.mode == "rule" and "Next session" in r.text and "generation" not in stages(r)
    w = layer(Boom()).respond("why this plan", decision(), plan)
    assert w.mode == "rule" and "structure=full_body" in w.text and "rule_based" in w.labels
    n = layer(Boom()).respond("how many calories do I need", decision(), plan, nutrition=estimate(prof(), GATE, BASE))
    assert n.mode == "rule" and "2483" in n.text and "3035" in n.text
    assert layer(Boom()).respond("calories?", decision(), plan, nutrition=estimate(prof(age=None), GATE, BASE)).uncertainty == "high"


def test_safety_before_everything(plan):
    r = layer().respond("what is my next session?", decision(age_years=15), plan)
    assert r.mode == "fixed" and stages(r)[:2] == ["context", "safety"] and "rule_engine" not in stages(r)


@pytest.mark.parametrize("t,why", [("can you diagnose my back", "refuse:medical"), ("my knee pain is bad, what now", "refuse:health-text")])
def test_refusals_never_reach_llm(plan, t, why):
    r = layer().respond(t, decision(), plan)
    assert r.mode == "fixed" and ("rule_engine", why) in r.trace and "generation" not in stages(r)


def test_technique_without_verified_source_is_uncertain_not_guessed(plan):
    r = layer(kb=ExerciseKnowledgeBase(load_starter())).respond("how to do bodyweight squat form", decision(), plan)
    assert r.mode == "uncertain" and ("uncertainty", "no-verified-source") in r.trace            # starter set is experimental => not retrievable


def test_technique_with_experimental_source_in_dev_is_labelled():
    rows = load_starter()
    kb = ExerciseKnowledgeBase(rows, allow_experimental=True)
    ch = kb.retrieve("how to do push up", ())
    assert ch and ch[0].status == "experimental"
    p = type("P", (), {"codes": ("push_up",), "structure": "x", "days": (), "reasons": (), "omissions": (), "confidence": "low"})()
    payload = {"text": "Keep a straight body line.", "exercises": ["push_up"], "claims": [{"text": "c", "source_id": "push_up"}], "uncertainty": "medium"}
    r = layer(StubProvider(payload), kb).respond("how to do push up", decision(), p)
    assert r.mode == "ai" and r.sources == ("push_up",) and r.labels == ("experimental_source",)


def test_free_question_with_no_sources_labelled(plan):
    r = layer().respond("tell me something motivating about training", decision(), plan)
    assert r.mode == "ai" and r.labels == ("no_sources",) and stages(r) == ["context", "safety", "rule_engine", "retrieval", "generation", "output_validation", "safety_validation"]


def test_provider_down_and_validator_and_safety_validation(plan):
    assert layer(StubProvider(fail=True)).respond("tell me something motivating", decision(), plan).mode == "fallback"
    bad = {"text": "ok", "exercises": ["deadlift"], "claims": [], "uncertainty": "low"}
    r = layer(StubProvider(bad)).respond("tell me something motivating", decision(), plan)
    assert r.mode == "fallback" and "SAF-R009:deadlift" in dict(r.trace)["generation"]
    quota = layer().respond("tell me something motivating", decision(), plan, quota_remaining=0)
    assert quota.mode == "fixed" and ("generation", "quota") in quota.trace


def test_prod_decision_unreviewed_content_blocks_ai():
    prod = RuleSet(version=1, status="p", screening_questions=QUESTIONS)
    d = evaluate(SafetyRequest("u", 30, True, {q: False for q in QUESTIONS}), prod)
    assert layer().respond("next session", d, None).mode == "fixed"

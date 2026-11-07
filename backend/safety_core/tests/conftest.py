import pytest
from safety_core import *  # noqa
from safety_core.models import (ClinicalRule, Condition, ExerciseCandidate, OutOfScopeFlag, REGIONS, RegionLoad,
                                Restriction, RuleSet, SafetyRequest)

QUESTIONS = ("chest_pain", "fainting")


def make_ex(code, loads=None, **kw):
    base = {r: "none" for r in REGIONS}
    base.update(loads or {})
    return ExerciseCandidate(code=code, review_status="published", safety_tags_complete=True,
                             movement_pattern=kw.pop("pattern", "squat"),
                             region_loads=tuple(RegionLoad(r, l) for r, l in base.items()), **kw)


@pytest.fixture
def rules():
    return RuleSet(version=1, status="test", screening_questions=QUESTIONS, allow_unreviewed_content=True)


@pytest.fixture
def req():
    def _make(**kw):
        d = dict(user_id="u1", age_years=30, consent_health_valid=True,
                 red_flag_answers={q: False for q in QUESTIONS}, candidates=(make_ex("squat"), make_ex("curl", pattern="curl")))
        d.update(kw)
        return SafetyRequest(**d)
    return _make

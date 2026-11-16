"""Advisory posture (DEC-ADVISORY): referral conditions become warnings; strict behaviour is covered in test_nutrition.py."""
import dataclasses

from nutrition_engine import NutritionProfile, estimate
from safety_core import SafetyCore
from safety_core.models import RuleSet, SafetyRequest

Q = ("chest_pain",)
STRICT = SafetyCore(RuleSet(version=1, status="t", screening_questions=Q, allow_unreviewed_content=True))
ADV = SafetyCore(RuleSet(version=1, status="t", screening_questions=Q, allow_unreviewed_content=True, advisory_mode=True))
BASE = SafetyRequest("u", 30, True, {"chest_pain": False})
SCR = {"eating_disorder_risk": False, "medical_diet_needed": False, "pregnant_or_lactating": False}


def prof(**scr):
    return NutritionProfile(age=30, sex="male", height_cm=180, weight_kg=80, activity="moderate", screening={**SCR, **scr})


def test_each_referral_is_warning_in_advisory_and_still_refer_in_strict():
    for key, code in (("eating_disorder_risk", "NUT-R02"), ("medical_diet_needed", "NUT-R04"), ("pregnant_or_lactating", "NUT-R04")):
        assert estimate(prof(**{key: True}), STRICT, BASE).status == "REFER"
        r = estimate(prof(**{key: True}), ADV, BASE)
        assert r.status == "OK" and r.tdee and code in r.reasons and "NUT-ADVISORY" in r.reasons and "advisory_see_doctor" in r.labels
        assert r.goal_adjustment == "disabled_pending_expert_review"        # never a deficit target


def test_no_advisory_noise_without_a_problem():
    r = estimate(prof(), ADV, BASE)
    assert r.status == "OK" and "NUT-ADVISORY" not in r.reasons and "advisory_see_doctor" not in r.labels

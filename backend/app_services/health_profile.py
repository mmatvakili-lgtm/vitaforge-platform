"""Consent, onboarding/profile and health inputs; builds the SafetyRequest (single translation point)."""
from __future__ import annotations

from safety_core.models import (CONDITION_STATUSES, OUT_OF_SCOPE_TYPES, PROBLEM_TYPES, REGIONS, SOURCES, Condition,
                                OutOfScopeFlag, Restriction, SafetyRequest)
from workout_engine.models import GOALS, LEVELS

from .errors import Forbidden, PreconditionRequired, ValidationFailed

CONSENT_HEALTH = "health_data_processing"


class HealthProfileService:
    def __init__(self, store, clock_days, screening_questions):
        self.s, self.today, self.questions = store, clock_days, tuple(screening_questions)

    # ---- consent (append-only)
    def give_consent(self, uid, doc_type, version, at=None):
        self.s.consents.append({"user": uid, "type": doc_type, "version": version, "granted": True, "day": self.today(), "at": at})

    def withdraw_consent(self, uid, doc_type, at=None):
        self.s.consents.append({"user": uid, "type": doc_type, "version": None, "granted": False, "day": self.today(), "at": at})

    def has_consent(self, uid, doc_type) -> bool:
        last = [c for c in self.s.consents if c["user"] == uid and c["type"] == doc_type]
        return bool(last) and last[-1]["granted"]

    # ---- onboarding
    def save_step(self, uid, step, data: dict):
        p = self.s.profiles.setdefault(uid, {"steps": {}, "complete": False})
        if step == "basics":
            age = data.get("age")
            if not isinstance(age, int) or not 0 < age < 120:
                raise ValidationFailed("age")
        elif step == "goal":
            if data.get("goal") not in GOALS or data.get("level") not in LEVELS:
                raise ValidationFailed("goal/level")
        elif step == "schedule":
            if not isinstance(data.get("days_per_week"), int) or not 1 <= data["days_per_week"] <= 6 \
                    or not isinstance(data.get("session_minutes"), int) or not 20 <= data["session_minutes"] <= 180:
                raise ValidationFailed("schedule")
        elif step == "equipment":
            if not isinstance(data.get("equipment"), list):
                raise ValidationFailed("equipment")
        else:
            raise ValidationFailed("step")
        p["steps"][step] = dict(data)
        p["complete"] = False

    def complete_onboarding(self, uid):
        p = self.s.profiles.get(uid) or {"steps": {}}
        missing = [x for x in ("basics", "goal", "schedule", "equipment") if x not in p["steps"]]
        if missing:
            raise ValidationFailed("missing:" + ",".join(missing))
        if not self.has_consent(uid, CONSENT_HEALTH):
            raise PreconditionRequired("consent_health")
        p["complete"] = True

    # ---- health inputs
    def _h(self, uid):
        return self.s.health.setdefault(uid, {"conditions": [], "restrictions": [], "flags": [], "answers": {}})

    def add_condition(self, uid, region, problem_type, status, source="self_reported", active_pain=False, worsening=False):
        if region not in REGIONS or problem_type not in PROBLEM_TYPES or status not in CONDITION_STATUSES or source not in SOURCES:
            raise ValidationFailed("condition")
        self._h(uid)["conditions"].append(Condition(region, problem_type, status, source, active_pain, worsening))

    def add_restriction(self, uid, actor_role, **kw):
        if actor_role not in ("professional", "admin"):          # users can never self-create professional restrictions
            raise Forbidden("restriction")
        self._h(uid)["restrictions"].append(Restriction(**kw))

    def add_out_of_scope(self, uid, flag_type, active=True):
        if flag_type not in OUT_OF_SCOPE_TYPES:
            raise ValidationFailed("flag")
        self._h(uid)["flags"].append(OutOfScopeFlag(flag_type, active))

    def answer_screening(self, uid, answers: dict):
        for k, v in answers.items():
            if k not in self.questions or not isinstance(v, bool):
                raise ValidationFailed("screening:" + str(k))
        self._h(uid)["answers"].update(answers)

    def safety_request(self, uid, candidates=(), context=None) -> SafetyRequest:
        p = self.s.profiles.get(uid, {"steps": {}})
        h = self._h(uid)
        answers = {q: h["answers"].get(q) for q in self.questions}
        consent = True if self.has_consent(uid, CONSENT_HEALTH) else (False if any(
            c["user"] == uid and c["type"] == CONSENT_HEALTH for c in self.s.consents) else None)
        return SafetyRequest(user_id=uid, age_years=p["steps"].get("basics", {}).get("age"), consent_health_valid=consent,
                             red_flag_answers=answers, out_of_scope_flags=tuple(h["flags"]),
                             conditions=tuple(h["conditions"]), restrictions=tuple(h["restrictions"]),
                             candidates=tuple(candidates), today_ordinal=self.today(), context=context or {})

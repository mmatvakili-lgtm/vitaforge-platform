"""Remaining MVP endpoints' use-cases: password reset, profile, consent documents, symptoms, versions, admin listings, grants."""
from __future__ import annotations

import hashlib
import secrets

from .errors import AuthFailed, Forbidden, Gone, NotFound, ValidationFailed
from .identity import hash_password

RESET_TTL = 30 * 60
CONSENT_DOCS = [{"type": "health_data_processing", "version": "v1", "status": "draft_pending_legal_review"},
                {"type": "terms", "version": "v1", "status": "draft_pending_legal_review"},
                {"type": "privacy", "version": "v1", "status": "draft_pending_legal_review"}]   # real text: OPEN-004


class MoreService:
    def __init__(self, store, identity, health, workouts, catalog, clock):
        self.s, self.id, self.h, self.w, self.cat, self.clock = store, identity, health, workouts, catalog, clock
        for k in ("resets", "grants"):
            self.s.__dict__.setdefault(k, {} if k == "resets" else [])

    # ---- password reset (token returned to the mail adapter; never to the API caller)
    def request_reset(self, email, token=None):
        uid = self.s.by_email.get((email or "").strip().lower())
        if not uid:
            return None                                   # API answers identically either way (no enumeration)
        token = token or secrets.token_urlsafe(32)
        idx = self.s.__dict__.setdefault("reset_index", {})
        old = idx.get(uid)
        if old:
            self.s.resets.pop(old, None)                  # a new request invalidates the previous token
        h = hashlib.sha256(token.encode()).hexdigest()
        self.s.resets[h] = {"user": uid, "exp": self.clock() + RESET_TTL}
        idx[uid] = h
        return token

    def confirm_reset(self, token, new_password):
        key = hashlib.sha256((token or "").encode()).hexdigest()
        r = self.s.resets.get(key)
        if not r:
            raise AuthFailed()
        if r["exp"] < self.clock():
            self.s.resets.pop(key, None)
            raise Gone("reset_token_expired")
        if len(new_password or "") < 10 or new_password.lower() == new_password or not any(c.isdigit() for c in new_password):
            raise ValidationFailed("password")                # a weak password does not burn the token
        self.s.resets.pop(key, None)                          # single use
        self.s.__dict__.setdefault("reset_index", {}).pop(r["user"], None)
        u = self.s.users[r["user"]]
        u["pw"], u["fails"], u["locked_until"] = hash_password(new_password), 0, 0
        for sess in self.s.sessions.values():             # revoke all sessions
            if sess["user"] == r["user"]:
                sess["revoked"] = True

    # ---- profile / onboarding / consents
    def get_profile(self, uid):
        u = self.s.users[uid]
        return {"email": u["email"], "locale": u["locale"], "plan": u["plan"], "role": u["role"], "prefs": dict(u.get("prefs", {}))}

    PREFS = ("display_name", "sex", "country", "timezone", "calendar", "unit_system", "digit_style")

    def patch_profile(self, uid, locale=None, prefs=None):
        if locale is not None:
            if locale not in ("fa", "en"):
                raise ValidationFailed("locale")
            self.s.users[uid]["locale"] = locale
        for k, v in (prefs or {}).items():
            if k not in self.PREFS:
                raise ValidationFailed("pref:" + k)
            self.s.users[uid].setdefault("prefs", {})[k] = v
        return self.get_profile(uid)

    def onboarding_state(self, uid):
        p = self.s.profiles.get(uid, {"steps": {}, "complete": False})
        return {"steps_done": sorted(p["steps"]), "complete": p["complete"]}

    def consent_documents(self):
        return {"documents": CONSENT_DOCS}

    # ---- health
    def update_condition(self, uid, idx, status):
        from safety_core.models import CONDITION_STATUSES
        conds = self.h._h(uid)["conditions"]
        if status not in CONDITION_STATUSES or not 0 <= idx < len(conds):
            raise ValidationFailed("condition")
        import dataclasses
        conds[idx] = dataclasses.replace(conds[idx], status=status)

    def add_symptom(self, uid, region, description):
        if not isinstance(description, str) or not 1 <= len(description) <= 500:
            raise ValidationFailed("description")
        self.h.add_condition(uid, region, "other", "self_reported_symptom", "self_reported", active_pain=False)

    # ---- workouts
    def plan_versions(self, uid):
        v = self.s.plans.get(uid)
        if not v:
            raise NotFound()
        return [{"version": x["version"], "cause": x["cause"], "day": x["day"], "codes": list(x["result"].codes)} for x in v]

    def alternatives(self, uid, code):
        if code not in self.s.catalog:
            raise NotFound()
        cands = [c.candidate for c in self.s.catalog.values()]
        catalog = {c.code: c.candidate for c in self.s.catalog.values()}
        req = self.h.safety_request(uid, cands)
        return {"alternatives": list(self.w.gate.find_alternatives(code, self.s.relations, catalog, req))}

    def list_sessions(self, uid):
        return {"sessions": [{"id": w["id"], "day_name": w["day_name"], "finished": w["finished"], "sets": len(w["logs"])}
                             for w in self.s.workout_sessions.values() if w["user"] == uid]}

    # ---- admin
    def admin_list_exercises(self, role):
        self._need(role, ("content_admin", "exercise_reviewer", "clinical_safety_reviewer", "admin"))
        return {"items": [{"code": c, "status": m["status"], "version": m["version"], "sample": m["sample"]} for c, m in sorted(self.s.exercise_meta.items())]}

    def admin_create_exercise(self, role, code, factory, sample=True):
        return self.cat.create_draft(role, code, factory, sample=sample)

    def admin_list_users(self, role):
        self._need(role, ("admin",))
        return {"users": [{"id": u["id"], "role": u["role"], "plan": u["plan"]} for u in self.s.users.values()]}   # no email/health data

    def admin_list_rule_sets(self, role):
        self._need(role, ("clinical_safety_reviewer", "admin"))
        return {"rule_sets": [{"version": v, **r} for v, r in sorted(self.s.rule_sets.items())]}

    def grant_health_access(self, uid, professional_id, scope="read"):
        """User-initiated, consented, revocable access for a professional (FR-PRO). Admin cannot grant on a user's behalf."""
        if professional_id not in self.s.users or self.s.users[professional_id]["role"] != "professional":
            raise NotFound()
        if scope not in ("read",):
            raise ValidationFailed("scope")
        g = {"user": uid, "professional": professional_id, "scope": scope, "day": self.clock(), "revoked": False}
        self.s.grants.append(g)
        return g

    def _need(self, role, allowed):
        if role not in allowed:
            raise Forbidden()

"""DEV adapter: stdlib WSGI JSON API over app_services (paths follow DOC-07 /api/v1).

NOT the production adapter (production = Django/DRF, ADR-0001/0007) and uses in-memory storage.
Exists so the full flow is runnable and testable in an environment without Django.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import re
import time
from datetime import date
from typing import Callable, List, Tuple

from app_services.catalog import CatalogService
from app_services.subscriptions import DisabledPaymentProvider, SubscriptionService
from app_services.extras import ExtrasService
from app_services.more import MoreService
from app_services.errors import AppError, AuthFailed, SafetyBlocked
from app_services.health_profile import CONSENT_HEALTH, HealthProfileService
from app_services.identity import IdentityService
from app_services.store import InMemoryStore
from app_services.workouts import WorkoutService
from safety_core import SafetyCore
from safety_core.models import RuleSet

SCREENING = ("chest_pain", "fainting", "severe_unexplained_pain", "neurological_symptoms")


def _plain(o):
    if dataclasses.is_dataclass(o):
        return {f.name: _plain(getattr(o, f.name)) for f in dataclasses.fields(o)}
    if isinstance(o, dict):
        return {k: _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_plain(x) for x in o]
    if hasattr(o, "value"):
        return o.value
    return o


class App:
    def __init__(self, store: InMemoryStore, rule_set: RuleSet, dev_mode: bool = False):
        self.dev = dev_mode
        day = lambda: date.today().toordinal()
        self.id = IdentityService(store, lambda: int(time.time()))
        self.h = HealthProfileService(store, day, SCREENING)
        self.w = WorkoutService(store, self.h, SafetyCore(rule_set), day)
        self.cat = CatalogService(store)
        self.sub = SubscriptionService(store, DisabledPaymentProvider())
        self.store = store
        self.x = ExtrasService(store, self.h, self.w, day)
        self.m = MoreService(store, self.id, self.h, self.w, self.cat, lambda: int(time.time()))
        from ai_gateway import AIGateway, StubProvider
        from ai_gateway.ports import ProviderUnavailable
        class _Unconfigured:
            code, external = 'unconfigured', False
            def generate(self, req): raise ProviderUnavailable('no provider configured')
        self.ai = AIGateway(StubProvider() if dev_mode else _Unconfigured())   # production: rule-based fallback until a provider is approved
        self.sent_resets: list = []     # dev 'mail outbox'
        self.routes: List[Tuple[str, "re.Pattern", Callable]] = []
        R = self._route
        R("GET", "/health/live", lambda c: {"status": "ok"}, auth=False)
        R("POST", "/auth/register", self._register, auth=False)
        R("POST", "/auth/verify", self._verify, auth=False)
        R("POST", "/auth/login", lambda c: {"token": self.id.login(c["body"].get("email"), c["body"].get("password"))}, auth=False)
        R("POST", "/auth/logout", lambda c: self.id.logout(c["token"]) or {})
        R("GET", "/auth/sessions", lambda c: {"sessions": self.id.list_sessions(c["uid"])})
        R("DELETE", "/auth/sessions/(?P<sid>[^/]+)", lambda c: self.id.revoke_session(c["uid"], c["sid"]) or {})
        R("POST", "/consents", lambda c: self.h.give_consent(c["uid"], c["body"].get("type", CONSENT_HEALTH), c["body"].get("version", "v1")) or {})
        R("PUT", "/onboarding/steps/(?P<step>[a-z0-9_]+)", lambda c: self.h.save_step(c["uid"], c["step"], c["body"]) or {})
        R("POST", "/onboarding/complete", lambda c: self.h.complete_onboarding(c["uid"]) or {"complete": True})
        R("POST", "/health/conditions", self._condition)
        R("POST", "/health/screening", lambda c: self.h.answer_screening(c["uid"], c["body"]) or {})
        R("POST", "/health/out-of-scope-flags", lambda c: self.h.add_out_of_scope(c["uid"], c["body"].get("flag_type")) or {})
        R("POST", "/workouts/generate", lambda c: _plain(self.w.generate(c["uid"])))
        R("GET", "/workouts/current", lambda c: _plain(self.w.current(c["uid"])))
        R("POST", "/workouts/plans/(?P<pid>[^/]+)/substitute", self._substitute)
        R("POST", "/workouts/sessions", lambda c: {"id": self.w.start_session(c["uid"], c["body"].get("day_name"))})
        R("POST", "/workouts/sessions/(?P<sid>[^/]+)/logs", self._log)
        R("POST", "/workouts/sessions/(?P<sid>[^/]+)/finish", lambda c: self.w.finish(c["uid"], c["sid"]) or {})
        R("GET", "/exercises", lambda c: {"items": self.cat.list_public()})
        R("GET", "/exercises/(?P<code>[^/]+)", lambda c: {"code": c["code"], "pattern": self.cat.get_public(c["code"]).candidate.movement_pattern})
        R("GET", "/subscriptions/plans", lambda c: {"plans": self.sub.plans()})
        R("GET", "/subscriptions/me", lambda c: self.sub.me(c["uid"]))
        R("POST", "/subscriptions/checkout", lambda c: self.sub.checkout(c["uid"], c["body"].get("plan")))
        R("POST", "/subscriptions/cancel", lambda c: self.sub.cancel(c["uid"]) or {})
        R("POST", "/admin/exercises/(?P<code>[^/]+)/transition", lambda c: {"status": self.cat.transition(
            self._role(c), c["uid"], c["code"], c["body"].get("target"), bool(c["body"].get("tags_complete")))["status"]})
        R("POST", "/admin/safety/rule-sets/(?P<v>[^/]+)/publish", lambda c: self.cat.publish_rule_set(
            self._role(c), c["uid"], self._int(c["v"]), c["body"].get("expert_signoff_ref")))
        R("PUT", "/admin/plans/(?P<plan>[a-z0-9]+)/features", lambda c: self.sub.set_plan_features(
            self._role(c), c["plan"], c["body"].get("features", [])) or {})
        R("POST", "/body/measurements", lambda c: self.x.add_measurement(c["uid"], c["body"].get("weight_kg"), c["body"].get("height_cm")) or {})
        R("GET", "/body/overview", lambda c: self.x.body_overview(c["uid"]))
        R("POST", "/health/pain-logs", lambda c: self.x.log_pain(c["uid"], c["body"].get("region"), c["body"].get("intensity")))
        R("GET", "/health/profile", lambda c: self.x.health_profile(c["uid"]))
        R("GET", "/dashboard", lambda c: self.x.dashboard(c["uid"]))
        R("GET", "/progress/monthly", lambda c: self.x.monthly_progress(c["uid"], date.today().toordinal() - 29, date.today().toordinal()))
        R("POST", "/privacy/export", self._export)
        R("POST", "/privacy/delete", self._delete)
        R("GET", "/privacy/requests/(?P<rid>[^/]+)", self._privacy_status)
        R("POST", "/ai/chat", self._chat)
        R("POST", "/admin/exercises", self._admin_create_exercise)
        R("POST", "/auth/password-reset/request", self._reset_req, auth=False)
        R("POST", "/auth/password-reset/confirm", lambda c: self.m.confirm_reset(c["body"].get("token"), c["body"].get("new_password")) or {}, auth=False)
        R("GET", "/profile", lambda c: self.m.get_profile(c["uid"]))
        R("PATCH", "/profile", lambda c: self.m.patch_profile(c["uid"], c["body"].get("locale")))
        R("GET", "/consents/documents", lambda c: self.m.consent_documents(), auth=False)
        R("GET", "/onboarding", lambda c: self.m.onboarding_state(c["uid"]))
        R("PATCH", "/health/conditions/(?P<i>[^/]+)", lambda c: self.m.update_condition(c["uid"], self._int(c["i"]), c["body"].get("status")) or {})
        R("POST", "/health/symptoms", lambda c: self.m.add_symptom(c["uid"], c["body"].get("region"), c["body"].get("description")) or {})
        R("GET", "/exercises/(?P<code>[^/]+)/alternatives", lambda c: self.m.alternatives(c["uid"], c["code"]))
        R("GET", "/workouts/plans/(?P<pid>[^/]+)/versions", lambda c: {"versions": self.m.plan_versions(c["uid"])})
        R("GET", "/workouts/sessions", lambda c: self.m.list_sessions(c["uid"]))
        R("GET", "/admin/exercises", lambda c: self.m.admin_list_exercises(self._role(c)))
        R("GET", "/admin/users", lambda c: self.m.admin_list_users(self._role(c)))
        R("GET", "/admin/safety/rule-sets", lambda c: self.m.admin_list_rule_sets(self._role(c)))
        R("POST", "/admin/health-access-grants", lambda c: self._deny_admin_grant(c))
        R("POST", "/health/access-grants", lambda c: self.m.grant_health_access(c["uid"], c["body"].get("professional_id")))
        R("GET", "/health/ready", lambda c: {"status": "ok"}, auth=False)
        R("GET", "/progress/weekly", lambda c: self.w.weekly_progress(c["uid"], date.today().toordinal() - 6, date.today().toordinal()))

    def _route(self, method, pattern, fn, auth=True):
        self.routes.append((method, re.compile("^/api/v1" + pattern + "$"), fn, auth))

    @staticmethod
    def _int(v):
        from app_services.errors import ValidationFailed
        try:
            return int(v)
        except ValueError:
            raise ValidationFailed("id")

    def _privacy_req(self, uid, kind):
        reqs = self.store.__dict__.setdefault("privacy_requests", {})
        rid = self.store.new_id("prq")
        reqs[rid] = {"user": uid, "kind": kind, "status": "completed"}
        return rid

    def _export(self, c):
        return {"request_id": self._privacy_req(c["uid"], "export"), "data": self.x.export(c["uid"])}

    def _delete(self, c):
        rid = self._privacy_req(c["uid"], "delete")
        self.x.erase(c["uid"])
        return {"request_id": rid, "erased": True}

    def _privacy_status(self, c):
        from app_services.errors import NotFound
        r = self.store.__dict__.get("privacy_requests", {}).get(c["rid"])
        if not r or r["user"] != c["uid"]:
            raise NotFound()
        return {"request_id": c["rid"], "kind": r["kind"], "status": r["status"]}

    def _chat(self, c):
        uid = c["uid"]
        acc = self.sub.access(uid, "ai_chat")
        plan = self.store.plans.get(uid)
        codes = plan[-1]["result"].codes if plan else ()
        decision = self.w.gate.evaluate(self.h.safety_request(uid, ()))
        names = list(codes)
        r = self.ai.respond(c["body"].get("message", ""), {"structure": plan[-1]["result"].structure if plan else None,
                            "exercise_names": names}, decision, codes,
                            quota_remaining=None if acc.allowed else 0)
        if r.reason == "quota":
            from app_services.errors import PaymentRequired
            raise PaymentRequired()                       # non-safety feature only; safety answers above are never gated
        return {"mode": r.mode, "text": r.text, "reason": r.reason, "decision_id": r.safety_decision_id}

    def _admin_create_exercise(self, c):
        from safety_core.models import REGIONS, ExerciseCandidate, RegionLoad
        from workout_engine.models import CatalogExercise
        from app_services.errors import ValidationFailed
        b = c["body"]
        loads = b.get("region_loads") or {}
        if set(loads) != set(REGIONS) or not b.get("code") or not b.get("movement_pattern"):
            raise ValidationFailed("exercise")
        cand = ExerciseCandidate(b["code"], "published", True, b["movement_pattern"], tuple(RegionLoad(r, l) for r, l in loads.items()))
        ex = CatalogExercise(cand, b.get("role", "accessory"), b.get("primary_muscle", "other"))
        return {"code": self.m.admin_create_exercise(self._role(c), b["code"], lambda: ex, True)}

    def _reset_req(self, c):
        tok = self.m.request_reset(c["body"].get("email"))
        if tok and self.dev:
            self.sent_resets.append(tok)                  # a real mail adapter sends it; never returned to the caller
        return {"accepted": True}

    def _deny_admin_grant(self, c):
        from app_services.errors import Forbidden
        raise Forbidden()                                 # only the user may grant access to their health data

    def _role(self, c):
        return self.store.users[c["uid"]]["role"]

    def _register(self, c):
        b = c["body"]
        uid = self.id.register(b.get("email"), b.get("password"), b.get("locale", "fa"))
        if self.dev:
            self.id.verify_email(uid)                      # dev only: no mail server
        return {"id": uid}

    def _verify(self, c):
        if not self.dev:
            raise AuthFailed()
        self.id.verify_email(c["body"].get("user_id")); return {}

    def _condition(self, c):
        b = c["body"]
        self.h.add_condition(c["uid"], b.get("region"), b.get("problem_type"), b.get("status"), "self_reported",
                             bool(b.get("active_pain")), bool(b.get("worsening")))
        return {}

    def _substitute(self, c):
        v = self.w.substitute(c["uid"], c["body"].get("code"), c["body"].get("reason", "other"))
        return _plain(v) if v else {"alternative": None, "message": "no_valid_alternative"}

    def _log(self, c):
        b = c["body"]
        self.w.log_set(c["uid"], c["sid"], b.get("code"), b.get("reps"), b.get("load_kg", 0), b.get("rpe"))
        return {}

    def __call__(self, environ, start_response):
        method, path = environ["REQUEST_METHOD"], environ["PATH_INFO"]
        if method == "GET" and path == "/":
            html = (pathlib.Path(__file__).parent / "static" / "index.html").read_bytes()
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(html))),
                                      ("X-Content-Type-Options", "nosniff"), ("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")])
            return [html]
        try:
            n = int(environ.get("CONTENT_LENGTH") or 0)
            if n > 100_000:
                return self._resp(start_response, 413, {"error": "too_large"})
            raw = environ["wsgi.input"].read(n) if n else b""
            body = json.loads(raw) if raw else {}
            if not isinstance(body, dict):
                return self._resp(start_response, 422, {"error": "validation_failed"})
        except (ValueError, UnicodeDecodeError):
            return self._resp(start_response, 400, {"error": "bad_json"})
        for m, rx, fn, auth in self.routes:
            mt = rx.match(path)
            if m == method and mt:
                ctx = {"body": body, **mt.groupdict()}
                try:
                    if auth:
                        h = environ.get("HTTP_AUTHORIZATION", "")
                        ctx["token"] = h[7:] if h.startswith("Bearer ") else ""
                        ctx["uid"] = self.id.authenticate(ctx["token"])
                    return self._resp(start_response, 200, fn(ctx))
                except SafetyBlocked as e:
                    return self._resp(start_response, e.http, {"error": e.code, "status": e.status,
                                                               "reasons": list(e.reasons), "decision_id": e.decision_id})
                except AppError as e:
                    return self._resp(start_response, e.http, {"error": e.code})
        return self._resp(start_response, 404, {"error": "not_found"})

    @staticmethod
    def _resp(start, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        start(f"{code} X", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data))),
                            ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")])
        return [data]

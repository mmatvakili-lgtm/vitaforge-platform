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
        R("PUT", "/onboarding/steps/(?P<step>[a-z_]+)", lambda c: self.h.save_step(c["uid"], c["step"], c["body"]) or {})
        R("POST", "/onboarding/complete", lambda c: self.h.complete_onboarding(c["uid"]) or {"complete": True})
        R("POST", "/health/conditions", self._condition)
        R("POST", "/health/screening", lambda c: self.h.answer_screening(c["uid"], c["body"]) or {})
        R("POST", "/health/out-of-scope-flags", lambda c: self.h.add_out_of_scope(c["uid"], c["body"].get("flag_type")) or {})
        R("POST", "/workouts/generate", lambda c: _plain(self.w.generate(c["uid"])))
        R("GET", "/workouts/current", lambda c: _plain(self.w.current(c["uid"])))
        R("POST", "/workouts/plans/current/substitute", self._substitute)
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
        R("POST", "/admin/safety/rule-sets/(?P<v>[0-9]+)/publish", lambda c: self.cat.publish_rule_set(
            self._role(c), c["uid"], int(c["v"]), c["body"].get("expert_signoff_ref")))
        R("PUT", "/admin/plans/(?P<plan>[a-z]+)/features", lambda c: self.sub.set_plan_features(
            self._role(c), c["plan"], c["body"].get("features", [])) or {})
        R("GET", "/progress/weekly", lambda c: self.w.weekly_progress(c["uid"], date.today().toordinal() - 6, date.today().toordinal()))

    def _route(self, method, pattern, fn, auth=True):
        self.routes.append((method, re.compile("^/api/v1" + pattern + "$"), fn, auth))

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

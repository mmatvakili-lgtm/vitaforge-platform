"""DEV adapter: stdlib WSGI JSON API over app_services. Routes, request validation, success/error statuses and the error
envelope are driven by the OpenAPI document (docs/02-architecture/07-OPENAPI-SPECIFICATION.yaml), so the adapter cannot
silently drift from DOC-07 (verified by contract/ tests).

NOT the production adapter (production = Django/DRF, ADR-0001/0007) and uses in-memory storage.
"""
from __future__ import annotations

import contextlib
import dataclasses
import hmac
import json
import pathlib
import re
import secrets
import time
import uuid
from datetime import date, datetime, timezone
from http.cookies import SimpleCookie
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs

from app_services.catalog import CatalogService
from app_services.errors import (AppError, AuthFailed, BadRequest, Conflict, ConsentRequired, FeatureUnavailable, Forbidden, Gone,
                                 NeedsContent, NotFound, PaymentRequired, PreconditionRequired, SafetyBlocked, ValidationFailed)
from app_services.extras import ExtrasService
from app_services.health_profile import CONSENT_HEALTH, HealthProfileService
from app_services.identity import SESSION_TTL, IdentityService
from app_services.more import CONSENT_DOCS, MoreService
from app_services.store import InMemoryStore
from app_services.subscriptions import FEATURES, DisabledPaymentProvider, SubscriptionService
from app_services.workouts import WorkoutService
from contract.spec import Operation, contract
from safety_core import SafetyCore
from safety_core.models import REGIONS, SafetyDecision
from safety_core.models import RuleSet

SCREENING = ("chest_pain", "fainting", "severe_unexplained_pain", "neurological_symptoms")
SCREENING_VERSION = 1
ID_NS = uuid.UUID("5d0b1f0e-8a3c-4c55-9f6e-0a1b2c3d4e5f")
ONBOARDING_STEPS = {1: "basics", 2: "goal", 3: "schedule", 4: "equipment"}      # steps 5..14 of DOC-07 are not built yet
STRUCT = {"auto": None, "full_body": "full_body", "upper_lower": "upper_lower", "push_pull_legs": "ppl"}
DOC_TYPE = {"health_data": CONSENT_HEALTH, "terms": "terms"}                     # DOC-07 type -> internal consent type
MESSAGES = {"validation_failed": "Request is invalid.", "auth_failed": "Authentication failed.", "account_locked": "Account is temporarily locked.",
            "conflict": "Request conflicts with the current state.", "not_found": "Not found.", "forbidden": "Not allowed.",
            "quota_or_plan_required": "Your plan does not include this feature.", "precondition_required": "A prerequisite step is missing.",
            "needs_content": "Not enough reviewed exercises for your equipment and restrictions.", "feature_unavailable": "This feature is not available yet.",
            "bad_request": "Bad request.", "gone": "This link or code has expired.", "consent_required": "Valid health-data consent is required.",
            "internal_error": "Internal error.", "csrf_failed": "CSRF check failed.", "bad_json": "Body is not valid JSON.", "too_large": "Body too large.", "rate_limited": "Too many requests. Try again later."}


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


def pub(kind: str, internal) -> str:
    """Stable public UUID for an internal identifier (internal ids never leave the adapter)."""
    return str(uuid.uuid5(ID_NS, f"{kind}:{internal}"))


def resolve(kind: str, public: str, candidates) -> object:
    for c in candidates:
        if pub(kind, c) == public:
            return c
    raise NotFound()


def iso(seconds: Optional[int] = None, day: Optional[int] = None) -> str:
    if seconds is not None:
        return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return date.fromordinal(day).strftime("%Y-%m-%dT00:00:00Z")


class Reply:
    def __init__(self, body, status: Optional[int] = None, headers: Optional[List[Tuple[str, str]]] = None):
        self.body, self.status, self.headers = body, status, headers or []


class App:
    def __init__(self, store: InMemoryStore, rule_set: RuleSet, dev_mode: bool = False, mail=None):
        self.dev = dev_mode
        self.contract = contract()
        day = lambda: date.today().toordinal()
        self.sec = lambda: int(time.time())
        self.id = IdentityService(store, self.sec)
        self.h = HealthProfileService(store, day, SCREENING)
        self.rule_set = rule_set
        self.w = WorkoutService(store, self.h, SafetyCore(rule_set), day, clock_s=self.sec)
        self.cat = CatalogService(store)
        self.sub = SubscriptionService(store, DisabledPaymentProvider())
        self.store = store
        self.x = ExtrasService(store, self.h, self.w, day)
        self.m = MoreService(store, self.id, self.h, self.w, self.cat, self.sec)
        from ai_gateway import AIGateway, StubProvider
        from ai_gateway.ports import ProviderUnavailable

        class _Unconfigured:
            code, external = "unconfigured", False
            def generate(self, req): raise ProviderUnavailable("no provider configured")
        self.ai = AIGateway(StubProvider() if dev_mode else _Unconfigured())   # production: rule-based fallback until a provider is approved
        from ai_gateway import DecisionLayer, ExerciseKnowledgeBase
        from nutrition_engine import NutritionConfig, NutritionLog
        self.layer = DecisionLayer(self.ai, ExerciseKnowledgeBase([], allow_experimental=dev_mode), "fa")
        self.nlog = NutritionLog(store, day)
        for _n in ("foods", "recipes", "price_quotes", "user_prices", "shopping_state"):
            store.__dict__.setdefault(_n, {})
        self.ncfg = NutritionConfig(show_unverified_ranges=dev_mode)
        self.records: Dict[str, object] = {}                 # exercise_catalog records by code (names/instructions for display)
        from mailer import DisabledSender, Outbox
        from mailer.runtime import MailRuntime
        from app_services.account_mail import AccountMail
        self.mail = mail or MailRuntime(DisabledSender(), secrets.token_hex(32), "http://localhost:3000")   # no runtime given: nothing is delivered
        self.outbox = Outbox(store, self.mail.sender, self.mail.secret, self.sec, self.mail.frontend_base_url)
        self.acct = AccountMail(store, self.outbox, self.m, self.id, self.mail.secret, self.sec)
        store.__dict__.setdefault("verification", {})
        store.__dict__.setdefault("symptoms", {})
        store.__dict__.setdefault("cond_meta", {})
        store.__dict__.setdefault("privacy_requests", {})
        self.routes: List[Tuple[str, "re.Pattern", Callable, bool, Optional[Operation]]] = []
        self._build_routes()

    # ------------------------------------------------------------------ routing (driven by the spec)
    def _build_routes(self):
        for op in self.contract.ops:
            fn = getattr(self, "op_" + op.id.replace("-", "_").lower(), None)
            if fn is None:
                raise RuntimeError(f"no handler for {op.id}")                  # an unimplemented spec operation must fail loudly at start-up
            rx = re.compile("^/api/v1" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", op.path) + "$")
            self.routes.append((op.method, rx, fn, op.secured, op))
        R = lambda m, p, fn: self.routes.append((m, re.compile("^/api/v1" + p + "$"), fn, True, None))
        # not in OpenAPI (nutrition is x-deferred; the rest are dev/engine extras)
        if self.dev and self.mail.sender.provider == "capture":     # explicit development configuration only (MAIL_PROVIDER=capture AND DJANGO_DEBUG=true)
            self.routes.append(("GET", re.compile("^/api/v1/dev/captured-mail$"), self._dev_captured_mail, False, None))
        R("GET", "/safety/explain", self._explain)
        R("POST", "/health/access-grants", lambda c: self.m.grant_health_access(c["uid"], c["body"].get("professional_id")))

    # ------------------------------------------------------------------ helpers
    def _role(self, c):
        r = self.store.users[c["uid"]]["role"]
        return "admin" if r == "super_admin" else r

    def _need_consent(self, uid):
        if not self.h.has_consent(uid, CONSENT_HEALTH):
            raise ConsentRequired()

    def _cands(self):
        return tuple(x.candidate for x in self.store.catalog.values())

    def _decision_obj(self, uid, extra: Optional[SafetyDecision] = None) -> SafetyDecision:
        return extra or self.w.gate.evaluate(self._request_for(uid))

    def _request_for(self, uid):
        import dataclasses as dc
        req = self.h.safety_request(uid, self._cands())
        st = self.store.profiles.get(uid, {"steps": {}})["steps"]
        return dc.replace(req, equipment=tuple(st.get("equipment", {}).get("equipment", [])) if "equipment" in st else None,
                          user_level=st.get("goal", {}).get("level"))

    def _decision(self, d: SafetyDecision) -> dict:
        out = {"decision_id": pub("decision", d.decision_id), "status": d.status.value,
               "reasons": [{"code": r, "message_key": r} for r in d.reasons], "rule_set_version": d.rule_set_version}
        if d.required_questions:
            out["required_questions"] = list(d.required_questions)
        if d.referral_urgency:
            out["referral"] = {"urgency": d.referral_urgency, "message_key": d.reasons[0] if d.reasons else "SAF-R100",
                               "content_status": d.content_status if d.content_status in ("draft_unreviewed", "clinical_reviewed", "published") else "draft_unreviewed"}
        return out

    def _summary(self, code):
        ce = self.store.catalog[code]
        r = self.records.get(code)
        out = {"id": pub("ex", code), "code": code, "has_media": False, "review_status": r.publication_status if r else "unreviewed",
               "movement_pattern": ce.candidate.movement_pattern,
               "muscles": list(r.primary_muscles + r.secondary_muscles) if r else [ce.primary_muscle],
               "equipment": list(r.equipment) if r else [], "difficulty": r.difficulty if r else "unspecified"}
        if r:
            out["name_en"] = r.name_en
            if r.name_fa:
                out["name"] = r.name_fa
        return out

    def _plan(self, uid, v) -> dict:
        res = v["result"]
        ver = v["version"]
        days = []
        for i, d in enumerate(res.days):
            exs = []
            for k, e in enumerate(d.exercises):
                role = getattr(self.store.catalog.get(e.code), "role", "accessory")
                r = self.records.get(e.code)
                exs.append({"workout_exercise_id": pub("wex", f"{uid}:{ver}:{i}:{k}"), "exercise_id": pub("ex", e.code),
                            "name": (r.name_fa or r.name_en) if r else e.code, "role": role if role in ("warmup", "main", "accessory", "cooldown") else "accessory",
                            "sets": [{"set_no": n + 1, "reps_min": e.reps_min, "reps_max": e.reps_max, "target_rpe": e.rpe, "rest_sec": e.rest_seconds}
                                     for n in range(e.sets)]})
            days.append({"day_id": pub("day", f"{uid}:{ver}:{i}"), "day_index": i, "title": d.name, "est_minutes": d.estimated_minutes, "exercises": exs})
        st = self.store.profiles.get(uid, {"steps": {}})["steps"]
        used = [self.records.get(e.code) for d in res.days for e in d.exercises]
        # Fail-closed labelling: "published" only when the rule set does not accept unreviewed content AND every exercise record is published.
        published = (not getattr(self.rule_set, "allow_unreviewed_content", False)) and bool(used) \
            and all(r is not None and r.publication_status == "published" for r in used)
        out = {"plan_id": pub("plan", uid), "version_no": ver, "structure": res.structure or "unknown",
               "rationale": {"content_status": "published" if published else "experimental_unreviewed", "reasons": list(res.reasons), "flags": list(res.flags), "label": res.label,
                             "omissions": [f"{o.day}:{o.slot}:{o.reason}" for o in res.omissions], "balance": _plain(res.balance)},
               "safety_decision_id": pub("decision", res.safety_decision_id), "days": days}
        if "goal" in st:
            out["goal"] = st["goal"].get("goal")
        if res.confidence in ("high", "medium", "low"):
            out["confidence"] = res.confidence
        return out

    def _cond(self, uid, idx, c) -> dict:
        meta = self.store.cond_meta.get((uid, idx), {})
        out = {"id": pub("cond", f"{uid}:{idx}"), "region": c.region, "problem_type": c.problem_type, "status": c.status, "source": c.source}
        for k in ("side", "trend", "self_severity"):
            if meta.get(k) is not None:
                out[k] = meta[k]
        return out

    def _onboarding(self, uid) -> dict:
        p = self.store.profiles.get(uid, {"steps": {}, "complete": False})
        done = [n for n, name in ONBOARDING_STEPS.items() if name in p["steps"]]
        missing = [n for n in ONBOARDING_STEPS if n not in done]
        h = self.store.health.get(uid, {"answers": {}})
        return {"status": "completed" if p.get("complete") else ("in_progress" if done else "not_started"),
                "current_step": min(missing) if missing else max(ONBOARDING_STEPS), "answers": {k: dict(v) for k, v in p["steps"].items()},
                "summary_ready": not missing, "safety_screening_complete": all(isinstance(h["answers"].get(q), bool) for q in SCREENING)}

    @staticmethod
    def _age(dob: date) -> int:
        t = date.today()
        return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))

    # ------------------------------------------------------------------ auth
    def op_api_auth_001(self, c):
        b = c["body"]
        if not b.get("email"):
            raise ValidationFailed("phone_registration_not_supported" if b.get("phone") else "email_required")
        dob = date.fromisoformat(b["date_of_birth"])
        if dob > date.today() or self._age(dob) < 18:
            raise ValidationFailed("under_18")
        try:
            uid = self.id.register(b["email"], b["password"], b.get("language", "fa"), dob=dob.isoformat())
        except Conflict:
            return {"message": "registered"}                    # identical answer for an existing address: no account enumeration
        self.acct._limit("verify", b["email"].strip().lower())   # the first message counts toward the resend cooldown
        self.acct.issue_verification(uid)                       # persistent token + outbox row; registration NEVER verifies the account by itself
        self._flush_mail()
        return {"message": "registered"}

    def _dev_captured_mail(self, c):
        """DEV ONLY (never registered unless the capture adapter is explicitly configured in debug): latest captured message for ?to=&kind=. Nothing was delivered."""
        q = lambda k: (c["query"].get(k) or [""])[0]
        row = self.mail.sender.latest(q("to"), q("kind") or "verification")
        if not row:
            raise NotFound()
        return {"delivered": False, "provider": "capture", "kind": row["kind"], "secret": row["secret"], "subject": row["subject"]}

    def _flush_mail(self):
        """Capture adapter only (no network): deliver in the same request so development needs no worker. Network adapters are drained by `manage.py process_outbox`."""
        if self.mail.sender.inline:
            for mid in self.acct.fresh:
                self.outbox.process_inline(mid)
        self.acct.fresh.clear()

    def op_api_auth_002(self, c):
        b = c["body"]
        self.acct.verify(b["identifier"], b["code"])
        return {"message": "verified"}

    def op_api_auth_009(self, c):
        self.acct.resend_verification(c["body"]["identifier"])
        self._flush_mail()
        return {"message": "accepted"}                          # identical for unknown, unverified and already verified addresses

    def op_api_auth_003(self, c):
        token = self.id.login(c["body"]["identifier"], c["body"]["password"], c["ua"])
        s = self.id.session_of(token)
        csrf = secrets.token_urlsafe(24)
        flags = "; Path=/; SameSite=Lax; Max-Age=%d" % SESSION_TTL
        sec = "" if self.dev else "; Secure"
        p = self.store.profiles.get(s["user"], {"steps": {}, "complete": False})
        return Reply({"user_id": pub("user", s["user"]), "expires_at": iso(s["exp"]),
                      "onboarding_status": "completed" if p.get("complete") else ("in_progress" if p["steps"] else "not_started")},
                     headers=[("Set-Cookie", f"sessionid={token}; HttpOnly{flags}{sec}"), ("Set-Cookie", f"csrftoken={csrf}{flags}{sec}")])

    def op_api_auth_004(self, c):
        self.id.logout(c["token"])
        return Reply({"message": "logged_out"}, headers=[("Set-Cookie", "sessionid=; HttpOnly; Path=/; Max-Age=0"), ("Set-Cookie", "csrftoken=; Path=/; Max-Age=0")])

    def op_api_auth_005(self, c):
        self.acct.request_reset(c["body"]["identifier"])
        self._flush_mail()
        return {"message": "accepted"}                          # same answer whether or not the account exists

    def op_api_auth_006(self, c):
        try:
            self.m.confirm_reset(c["body"]["token"], c["body"]["new_password"])
        except AuthFailed:
            raise BadRequest("invalid_token")
        return {"message": "password_changed"}

    def op_api_auth_007(self, c):
        return [{"id": pub("session", s["id"]), "last_seen_at": iso(s["seen"]), "user_agent": s["device"], "current": s["token_hash"] == self.id._th(c["token"])}
                for s in self.id.list_sessions(c["uid"])]

    def op_api_auth_008(self, c):
        sid = resolve("session", c["session_id"], [s["id"] for s in self.id.list_sessions(c["uid"])])
        self.id.revoke_session(c["uid"], sid)
        return {"message": "revoked"}

    # ------------------------------------------------------------------ profile / privacy
    def _profile(self, uid):
        pr = self.m.get_profile(uid)
        out = {"language": pr["locale"], "onboarding_status": self._onboarding(uid)["status"]}
        out.update(pr["prefs"])
        return out

    def op_api_pro_001(self, c):
        return self._profile(c["uid"])

    def op_api_pro_002(self, c):
        b = dict(c["body"])
        self.m.patch_profile(c["uid"], b.pop("language", None), b)
        return self._profile(c["uid"])

    def _docs(self):
        out = []
        for d in CONSENT_DOCS:
            t = next((k for k, v in DOC_TYPE.items() if v == d["type"]), None)
            if t:
                out.append({"id": pub("doc", t), "type": t, "version": 0, "locale": "fa",
                            "body": "[پیش‌نویس — در انتظار بازبینی حقوقی (OPEN-004)؛ متن نهایی وجود ندارد و این رضایت‌نامه برای کاربر واقعی معتبر نیست]"})
        return out

    def op_api_priv_001(self, c):
        return self._docs()

    def op_api_priv_002(self, c):
        d = next((x for x in self._docs() if x["id"] == c["body"]["document_id"]), None)
        if not d:
            raise NotFound()
        now = self.sec()
        if c["body"]["granted"]:
            self.h.give_consent(c["uid"], DOC_TYPE[d["type"]], f"v{d['version']}", at=now)
        else:
            self.h.withdraw_consent(c["uid"], DOC_TYPE[d["type"]], at=now)
        n = len([x for x in self.store.consents if x["user"] == c["uid"]])
        return {"id": pub("consent", f"{c['uid']}:{n}"), "type": d["type"], "granted": c["body"]["granted"], "granted_at": iso(now)}

    def _privacy_req(self, uid, kind, **extra):
        rid = self.store.new_id("prq")
        self.store.privacy_requests[rid] = {"user": uid, "kind": kind, "status": "requested", **extra}
        return rid

    def op_api_priv_003(self, c):
        # DOC-07 has no download endpoint for the export artifact (gap recorded as OPEN-009): the request is stored, status stays 'requested'
        rid = self._privacy_req(c["uid"], "export", data=self.x.export(c["uid"]))
        return {"id": pub("prq", rid), "type": "export", "status": "requested"}

    def op_api_priv_004(self, c):
        from app_services.identity import verify_password
        if not verify_password(c["body"]["password"], self.store.users[c["uid"]]["pw"]):
            raise BadRequest("invalid_password")
        rid = self._privacy_req(c["uid"], "delete")
        self.x.erase(c["uid"])
        self.store.privacy_requests[rid]["status"] = "completed"
        return {"id": pub("prq", rid), "type": "delete", "status": "completed"}

    def op_api_priv_005(self, c):
        rid = resolve("prq", c["request_id"], [k for k, v in self.store.privacy_requests.items() if v["user"] == c["uid"]])
        r = self.store.privacy_requests[rid]
        return {"id": pub("prq", rid), "type": r["kind"], "status": r["status"]}

    # ------------------------------------------------------------------ onboarding
    def op_api_onb_001(self, c):
        return self._onboarding(c["uid"])

    def op_api_onb_002(self, c):
        try:
            n = int(c["step"])
        except ValueError:
            raise BadRequest("step")
        if not 1 <= n <= 14:
            raise BadRequest("step")
        if n not in ONBOARDING_STEPS:
            raise ValidationFailed("step_not_supported")
        self.h.save_step(c["uid"], ONBOARDING_STEPS[n], c["body"]["answers"])
        return self._onboarding(c["uid"])

    def op_api_onb_003(self, c):
        self.h.complete_onboarding(c["uid"])
        return self._onboarding(c["uid"])

    # ------------------------------------------------------------------ body
    def op_api_body_001(self, c):
        return self.x.overview(c["uid"])

    def op_api_body_002(self, c):
        b = c["body"]
        r = self.x.add_metric(c["uid"], b["metric"], b["value"], b["unit"], b["source"], b.get("method"))
        return {"id": pub("metric", f"{c['uid']}:{r['n']}"), "metric": r["metric"], "value": r["value"], "unit": r["unit"], "source": r["source"],
                "measured_at": b.get("measured_at") or iso(self.sec())}

    # ------------------------------------------------------------------ health
    @staticmethod
    def _active_pain(problem_type, severity):
        """Conservative derivation (EXP-014): pain with unknown severity counts as active; severity 0 means no current pain."""
        return problem_type == "pain" and severity != 0

    def op_api_health_001(self, c):
        self._need_consent(c["uid"])
        conds = self.store.health.get(c["uid"], {"conditions": [], "flags": []})
        return {"conditions": [self._cond(c["uid"], i, x) for i, x in enumerate(conds["conditions"])],
                "out_of_scope": [f.flag_type for f in conds["flags"] if f.active], "latest_decision": self._decision(self._decision_obj(c["uid"]))}

    def op_api_health_002(self, c):
        self._need_consent(c["uid"])
        b = c["body"]
        sev = b.get("self_severity")
        self.h.add_condition(c["uid"], b["region"], b["problem_type"], "self_reported_symptom", "self_reported",
                             self._active_pain(b["problem_type"], sev), b.get("trend") == "worse")
        idx = len(self.store.health[c["uid"]]["conditions"]) - 1
        self.store.cond_meta[(c["uid"], idx)] = {k: b.get(k) for k in ("side", "trend", "self_severity", "onset_date", "aggravating_factors", "relieving_factors")}
        return self._cond(c["uid"], idx, self.store.health[c["uid"]]["conditions"][idx])

    def op_api_health_003(self, c):
        self._need_consent(c["uid"])
        conds = self.store.health.get(c["uid"], {"conditions": []})["conditions"]
        idx = resolve("cond", c["condition_id"], [f"{c['uid']}:{i}" for i in range(len(conds))])
        i = int(idx.split(":")[1])
        meta = self.store.cond_meta.setdefault((c["uid"], i), {})
        meta.update({k: v for k, v in c["body"].items()})
        cur = conds[i]
        sev = meta.get("self_severity")
        conds[i] = dataclasses.replace(cur, active_pain=self._active_pain(cur.problem_type, sev) if "self_severity" in c["body"] else cur.active_pain,
                                       worsening=(meta.get("trend") == "worse") if "trend" in c["body"] else cur.worsening)
        return self._cond(c["uid"], i, conds[i])

    def op_api_health_004(self, c):
        self._need_consent(c["uid"])
        b = c["body"]
        sev = b.get("severity")
        self.h.add_condition(c["uid"], b["region"], "other", "self_reported_symptom", "self_reported", active_pain=bool(sev))
        rows = self.store.symptoms.setdefault(c["uid"], [])
        rows.append({"context": b["context"], "region": b["region"], "severity": sev, "note": b.get("note"), "ts": self.sec()})
        return {"id": pub("symptom", f"{c['uid']}:{len(rows)}"), "recorded_at": iso(rows[-1]["ts"])}

    def op_api_health_005(self, c):
        self._need_consent(c["uid"])
        b = c["body"]
        self.x.log_pain(c["uid"], b["region"], b["intensity"], b.get("session_id"))
        n = len(self.store.pain_logs[c["uid"]])
        return {"id": pub("pain", f"{c['uid']}:{n}"), "decision": self._decision(self._decision_obj(c["uid"]))}

    def op_api_health_006(self, c):
        self._need_consent(c["uid"])
        b = c["body"]
        if b["screening_version"] != SCREENING_VERSION:
            raise ValidationFailed("screening_version")
        self.h.answer_screening(c["uid"], b["answers"])
        return self._decision(self._decision_obj(c["uid"]))

    def op_api_health_007(self, c):
        self._need_consent(c["uid"])
        self.h.add_out_of_scope(c["uid"], c["body"]["flag_type"])
        return self._decision(self._decision_obj(c["uid"]))

    # ------------------------------------------------------------------ exercises
    def op_api_ex_001(self, c):
        q = c["query"]
        def one(k): return (q.get(k) or [None])[0]
        try:
            page, size = int(one("page") or 1), int(one("page_size") or 20)
        except ValueError:
            raise BadRequest("pagination")
        if page < 1 or not 1 <= size <= 100:
            raise BadRequest("pagination")
        rows = [self._summary(code) for code in self.cat.list_public()]
        def has(r, k, key): return one(k) is None or one(k) in r[key]
        needle = (one("q") or "").lower()
        rows = [r for r in rows if has(r, "muscle", "muscles") and has(r, "equipment", "equipment")
                and (one("difficulty") is None or r["difficulty"] == one("difficulty"))
                and (one("pattern") is None or self.store.catalog[r["code"]].candidate.movement_pattern == one("pattern"))
                and (not needle or needle in (r["code"] + " " + r.get("name", "") + " " + r.get("name_en", "")).lower())]
        out = {"count": len(rows), "results": rows[(page - 1) * size: page * size]}
        if page * size < len(rows):
            out["next"] = f"?page={page + 1}&page_size={size}"
        return out

    def op_api_ex_002(self, c):
        code = resolve("ex", c["exercise_id"], self.cat.list_public())
        s = self._summary(code)
        r = self.records.get(code)
        d = self.w.gate.evaluate(dataclasses.replace(self._request_for(c["uid"]), candidates=(self.store.catalog[code].candidate,)))
        item = next((i for i in d.per_item if i.code == code), None)
        comp = ({"status": "unknown", "reasons": list(d.reasons)} if not d.status.permits_content or item is None else
                {"status": "blocked" if not item.allowed else ("caution" if item.caution else "allowed"), "reasons": list(item.reasons)})
        out = {"id": s["id"], "code": code, "name": s.get("name", code), "name_en": s.get("name_en", code), "compatibility": comp,
               "steps": list(r.instructions) if r else [], "common_mistakes": list(r.common_mistakes) if r else [],
               "review_status": r.publication_status if r else "unreviewed", "media": []}
        if r and r.description:
            out["description"] = r.description
        if r and r.breathing:
            out["breathing"] = r.breathing
        if r and (r.limitations or r.safety_cautions):
            out["safety_notes"] = " ".join(r.safety_cautions + r.limitations)
        if r:
            from exercise_catalog import served_media
            out["media"] = [{"type": m.kind, "url": m.url} for m in served_media(r)]
        return out

    def op_api_ex_003(self, c):
        code = resolve("ex", c["exercise_id"], self.cat.list_public())
        alts = self.m.alternatives(c["uid"], code)["alternatives"]
        return {"alternatives": [self._summary(a) for a in alts if a in self.store.catalog], "none_valid": not alts,
                "decision": self._decision(self._decision_obj(c["uid"]))}

    # ------------------------------------------------------------------ workouts
    def op_api_wo_001(self, c):
        b = c["body"]
        ps = b.get("preferred_structure", "auto")
        if ps not in STRUCT:
            raise ValidationFailed("structure_not_supported")
        try:
            v = self.w.generate(c["uid"], STRUCT[ps])
        except SafetyBlocked as e:
            if e.decision is None or e.decision.status.permits_content:
                raise ValidationFailed("generation_failed")          # engine fail-safe without a blocking decision: no plan, nothing to show
            return {"decision": self._decision(e.decision), "plan": None}
        return {"decision": self._decision(v["decision"]), "plan": self._plan(c["uid"], v)}

    def op_api_wo_002(self, c):
        return self._plan(c["uid"], self.w.current(c["uid"]))

    def op_api_wo_003(self, c):
        if c["plan_id"] != pub("plan", c["uid"]) or not self.w.s.plans.get(c["uid"]):
            raise NotFound()
        return [{"version_no": v["version"], "created_at": iso(v["ts"]) if v.get("ts") else iso(day=v["day"]),
                 "safety_decision_id": pub("decision", v["result"].safety_decision_id)} for v in self.w.s.plans[c["uid"]]]

    def op_api_wo_004(self, c):
        if c["plan_id"] != pub("plan", c["uid"]):
            raise NotFound()
        cur = self.w.current(c["uid"])
        found = None
        for i, d in enumerate(cur["result"].days):
            for k, e in enumerate(d.exercises):
                if pub("wex", f"{c['uid']}:{cur['version']}:{i}:{k}") == c["body"]["workout_exercise_id"]:
                    found = e.code
        if found is None:
            raise NotFound()
        v = self.w.substitute(c["uid"], found, c["body"]["reason"])
        if v is None:
            raise Conflict("no_valid_alternative")
        return self._plan(c["uid"], v)

    def _session(self, w):
        done = [l for l in w["logs"] if not l.get("skipped")]
        out = {"id": pub("wks", w["id"]), "status": ("aborted" if w.get("aborted_reason") else "completed") if w["finished"] else "in_progress",
               "started_at": iso(w["start_ts"]) if w.get("start_ts") else iso(day=w["start"]), "day_title": w.get("day_name", ""),
               "sets_done": len(done), "volume_kg": sum(l["reps"] * l["load_kg"] for l in done),
               "logged_sets": [{"exercise_id": pub("ex", l["code"]), "set_no": l.get("set_no") or 0, "reps": l["reps"], "load_kg": l["load_kg"],
                                "skipped": bool(l.get("skipped")), "personal_record": bool(l.get("pr"))} for l in w["logs"]]}
        if w["finished"]:
            if w.get("start_ts") is not None and w.get("end_ts") is not None:
                out["duration_min"] = (w["end_ts"] - w["start_ts"]) // 60
            if w.get("perceived_difficulty") is not None:
                out["perceived_difficulty"] = w["perceived_difficulty"]
            if w.get("aborted_reason"):
                out["aborted_reason"] = w["aborted_reason"]
        return out

    def op_api_log_001(self, c):
        if not self.store.plans.get(c["uid"]):
            raise Conflict("no_active_plan")
        cur = self.w.current(c["uid"])
        try:
            i = resolve("day", c["body"]["day_id"], [f"{c['uid']}:{cur['version']}:{n}" for n in range(len(cur["result"].days))])
        except NotFound:
            raise ValidationFailed("day_id")                  # the id sits in the body, so this is a semantic error (LOG-001 declares no 404)
        name = cur["result"].days[int(i.rsplit(":", 1)[1])].name
        sid = self.w.start_session(c["uid"], name, self.sec())
        return self._session(self.store.workout_sessions[sid])

    def op_api_log_004(self, c):
        return [self._session(w) for w in self.store.workout_sessions.values() if w["user"] == c["uid"]]

    def op_api_log_002(self, c):
        b = c["body"]
        sid = resolve("wks", c["session_id"], [k for k, w in self.store.workout_sessions.items() if w["user"] == c["uid"]])
        cur = self.w.current(c["uid"])["result"]
        code = next((x for x in cur.codes if pub("ex", x) == b["exercise_id"]), None)
        if code is None:
            raise ValidationFailed("exercise_not_in_plan")
        e, created = self.w.log_set(c["uid"], sid, code, b.get("reps"), b.get("load_kg", 0), b.get("rpe"), client_uuid=b["client_uuid"],
                                    set_no=b["set_no"], skipped=bool(b.get("skipped")), duration_sec=b.get("duration_sec"))
        return {"id": pub("log", f"{sid}:{b['client_uuid']}"), "client_uuid": b["client_uuid"], "personal_record": bool(e.get("pr"))}

    def op_api_log_003(self, c):
        b = c["body"]
        sid = resolve("wks", c["session_id"], [k for k, w in self.store.workout_sessions.items() if w["user"] == c["uid"]])
        s = self.w.finish(c["uid"], sid, self.sec(), b.get("perceived_difficulty"), b.get("aborted_reason"), b.get("notes"))
        out = {"id": pub("wks", sid), "volume_kg": s["volume_kg"], "sets_done": s["sets_done"]}
        if s["duration_min"] is not None:
            out["duration_min"] = s["duration_min"]
        return out

    # ------------------------------------------------------------------ progress / dashboard
    def _report(self, uid, days, period):
        t = date.today().toordinal()
        r = self.w.weekly_progress(uid, t - days + 1, t)
        plan = self.store.plans.get(uid)
        planned = len(plan[-1]["result"].days) if plan else 0
        out = {"period": period, "planned_sessions": planned, "completed_sessions": r["sessions"], "volume_kg": r["volume_kg"], "records": [], "notes": []}
        if planned and days == 7:
            out["adherence_pct"] = round(100 * min(r["sessions"], planned) / planned, 1)
        return out

    def op_api_prog_001(self, c):
        return self._report(c["uid"], 7, "last_7_days")

    def op_api_prog_002(self, c):
        return self._report(c["uid"], 30, "last_30_days")

    def op_api_dash_001(self, c):
        uid = c["uid"]
        plan = self.store.plans.get(uid)
        d = self._decision_obj(uid)
        t = date.today().toordinal()
        return {"today": {"date": date.today().isoformat()},
                "current_plan": ({"version_no": plan[-1]["version"], "label": plan[-1]["result"].label} if plan else {}),
                "weekly_summary": self.w.weekly_progress(uid, t - 6, t), "alerts": [] if d.status.permits_content else [self._decision(d)]}

    # ------------------------------------------------------------------ subscriptions / AI
    def _plan_catalog(self):
        cat = self.sub.catalog
        return {"plans": [{"code": p, "is_free": p == "free", "quotas": {k: v for k, v in (cat.quotas.get(p, {}) or {}).items()},
                           "features": [{"code": f, "enabled": f in cat.plan_features[p], "safety_critical": cat.features[f].safety_critical} for f in sorted(cat.features)]}
                          for p in sorted(cat.plan_features)]}

    def op_api_sub_001(self, c):
        return self._plan_catalog()

    def _me(self, uid):
        s = self.sub.me(uid)
        return {"plan_code": s["plan"], "status": "active" if s["active"] else "inactive", "quotas_remaining": {}}

    def op_api_sub_002(self, c):
        return self._me(c["uid"])

    def op_api_sub_003(self, c):
        try:
            return self.sub.checkout(c["uid"], c["body"]["plan_code"])
        except ValidationFailed:
            raise BadRequest("plan_code")

    def op_api_sub_004(self, c):
        self.sub.cancel(c["uid"])
        return self._me(c["uid"])

    def op_api_ai_001(self, c):
        uid = c["uid"]
        acc = self.sub.access(uid, "ai_chat")
        plan = self.store.plans.get(uid)
        d = self._decision_obj(uid)
        r = self.layer.respond(c["body"]["message"], d, plan[-1]["result"] if plan else None, self._nut_result(uid), quota_remaining=None if acc.allowed else 0)
        if ("generation", "quota") in r.trace or (r.mode == "fixed" and r.trace and r.trace[-1][1] == "quota"):
            raise PaymentRequired()                       # non-safety feature only; safety/rule answers are never gated
        return {"answer": r.text, "uncertainty": r.uncertainty if r.uncertainty in ("none", "low", "medium", "high") else "high",
                "sources": list(r.sources), "mode": "llm" if r.mode == "ai" else "rule_based_fallback", "decision": self._decision(d)}

    # ------------------------------------------------------------------ admin
    def _admin_ex(self, m):
        return {"id": pub("adm_ex", m["code"]), "stable_code": m["code"], "review_status": m["status"], "version": m["version"],
                "safety_tags_complete": bool(m.get("tags_complete"))}

    def op_api_adm_001(self, c):
        self.m.admin_list_exercises(self._role(c))
        return [self._admin_ex(m) for _, m in sorted(self.store.exercise_meta.items())]

    def op_api_adm_002(self, c):
        from safety_core.models import LOADINGS, ExerciseCandidate, RegionLoad
        from workout_engine.models import CatalogExercise
        b = c["body"]
        loads = b.get("region_loads") or {}
        complete = set(loads) == set(REGIONS) and all(v in LOADINGS for v in loads.values())
        base = {r: loads.get(r, "high") for r in REGIONS}            # unknown region load is treated as 'high' (never optimistic)
        cand = ExerciseCandidate(b["stable_code"], "published", complete, b["movement_pattern"], tuple(RegionLoad(r, l) for r, l in base.items()))
        muscles = b.get("muscles") or ["other"]
        ex = CatalogExercise(cand, "accessory", muscles[0])
        self.cat.create_draft(self._role(c), b["stable_code"], lambda: ex, sample=True, tags_complete=complete)
        return self._admin_ex(self.store.exercise_meta[b["stable_code"]])

    def op_api_adm_003(self, c):
        role = self._role(c)
        code = next((k for k in self.store.exercise_meta if pub("adm_ex", k) == c["exercise_id"]), "__unknown__")
        meta = self.store.exercise_meta.get(code, {})
        try:
            self.cat.transition(role, c["uid"], code, c["body"]["to_status"], bool(meta.get("tags_complete")))
        except ValidationFailed as e:
            raise Conflict(e.detail)                       # an invalid/unsafe lifecycle move is a state conflict
        return self._admin_ex(self.store.exercise_meta[code])

    def op_api_adm_004(self, c):
        rows = self.m.admin_list_rule_sets(self._role(c))["rule_sets"]
        return [self._rule_set(r["version"], r) for r in rows]

    def _rule_set(self, version, r):
        out = {"id": pub("rs", version), "version": version, "status": r["status"]}
        if r.get("by"):
            out["reviewed_by"] = pub("user", r["by"])
        return out

    def op_api_adm_005(self, c):
        role = self._role(c)
        if role != "clinical_safety_reviewer":
            raise Forbidden()
        known = dict(self.store.rule_sets)
        version = resolve("rs", c["rule_set_id"], list(known))
        if known[version]["status"] == "published":
            raise Conflict("already_published")
        # DOC-07 has no sign-off reference field: `notes` carries the external expert approval reference and must be non-empty
        r = self.cat.publish_rule_set(role, c["uid"], version, c["body"].get("notes"))
        return self._rule_set(version, r)

    def op_api_adm_006(self, c):
        rows = self.m.admin_list_users(self._role(c))["users"]
        return [{"id": pub("user", u["id"]), "status": "active", "roles": [u["role"]]} for u in rows]

    def op_api_adm_007(self, c):
        raise Forbidden()                                  # only the data subject may grant access to their health data (privacy > admin convenience)

    def op_api_adm_008(self, c):
        role = self._role(c)
        plan = resolve("plan_code", c["plan_id"], list(self.sub.catalog.plan_features))
        feats = set(self.sub.catalog.plan_features[plan])
        for f in c["body"]["features"]:
            (feats.add if f["enabled"] else feats.discard)(f["code"])
        self.sub.set_plan_features(role, plan, feats)
        return self._plan_catalog()

    # ------------------------------------------------------------------ system
    def op_api_sys_001(self, c):
        return {"message": "ok"}

    def op_api_sys_002(self, c):
        return {"message": "ok"}

    # ------------------------------------------------------------------ non-OpenAPI extras (nutrition is x-deferred)
    def _nut_profile(self, uid):
        from nutrition_engine import NutritionProfile
        n = self.store.__dict__.get("nutrition_profiles", {}).get(uid)
        if not n:
            return None
        age = self.store.profiles.get(uid, {"steps": {}})["steps"].get("basics", {}).get("age")
        return NutritionProfile(age, n.get("sex"), n.get("height_cm"), n.get("weight_kg"), n.get("activity"), n.get("goal") or "maintain", n.get("screening", {}))

    def _nut_result(self, uid):
        from nutrition_engine import estimate
        p = self._nut_profile(uid)
        return estimate(p, self.w.gate, self.h.safety_request(uid, ()), self.ncfg) if p else None

    _NUT_PROFILE_KEYS = {"sex", "height_cm", "weight_kg", "activity", "goal", "screening", "allergens", "diet_required"}
    _MEAL_REQ_KEYS = {"days", "allergens", "excluded_food_ids", "diet_required", "max_cook_minutes", "weekly_budget", "currency", "region", "pantry"}

    @staticmethod
    def _strict(body, allowed, what):
        if not isinstance(body, dict) or set(body) - allowed:
            raise ValidationFailed(what)                                   # unknown keys are rejected, never stored (mass-assignment protection)

    def _nut_out(self, n):
        d = _plain(n)
        d["safety_decision_id"] = pub("decision", n.safety_decision_id) if n.safety_decision_id else None
        return d

    def _nut_out_for(self, uid, n):
        d = self._nut_out(n)
        p = self.store.__dict__.get("nutrition_profiles", {}).get(uid) or {}
        d["allergens"], d["diet_required"] = list(p.get("allergens") or []), list(p.get("diet_required") or [])
        return d

    def op_api_nut_001(self, c):
        self._need_consent(c["uid"])
        b = c["body"]
        self._strict(b, self._NUT_PROFILE_KEYS, "nutrition_profile")
        sc = b.get("screening")
        if not isinstance(sc, dict) or set(sc) != {"eating_disorder_risk", "medical_diet_needed", "pregnant_or_lactating"} or not all(isinstance(v, bool) for v in sc.values()):
            raise ValidationFailed("screening")
        for k, lo, hi in (("height_cm", 100, 250), ("weight_kg", 25, 400)):
            v = b.get(k)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
                raise ValidationFailed(k)
        if b.get("activity") not in ("sedentary", "light", "moderate", "active", "very_active") or b.get("goal", "maintain") not in ("maintain", "lose", "gain") \
                or b.get("sex") not in (None, "male", "female"):
            raise ValidationFailed("activity/goal/sex")
        from nutrition_engine.food import ALLERGENS, DIET_TAGS
        for k, vocab in (("allergens", ALLERGENS), ("diet_required", DIET_TAGS)):
            v = b.get(k, [])
            if not isinstance(v, list) or len(v) > len(vocab) or any(x not in vocab for x in v) or len(set(v)) != len(v):
                raise ValidationFailed(k)
        self.store.__dict__.setdefault("nutrition_profiles", {})[c["uid"]] = {k: b.get(k) for k in self._NUT_PROFILE_KEYS}
        return self._nut_out_for(c["uid"], self._nut_result(c["uid"]))

    def op_api_nut_002(self, c):
        self._need_consent(c["uid"])
        n = self._nut_result(c["uid"])
        if n is None:
            raise NotFound("nutrition_profile")
        return self._nut_out_for(c["uid"], n)

    def op_api_nut_003(self, c):
        """Weekly meal plan from the food/recipe/price data actually in the store. With no reviewed data the honest answer is NEEDS_CONTENT."""
        from datetime import date as _d
        from nutrition_engine import MealPlanRequest, plan_week, PriceBook
        self._need_consent(c["uid"])
        b = c["body"] or {}
        self._strict(b, self._MEAL_REQ_KEYS, "meal_plan_request")
        n = self._nut_result(c["uid"])
        if n is None:
            raise NotFound("nutrition_profile")
        foods = self.store.__dict__.setdefault("foods", {})
        recipes = list(self.store.__dict__.setdefault("recipes", {}).values())
        prof = self.store.__dict__.get("nutrition_profiles", {}).get(c["uid"]) or {}
        mine = [self._user_quote(q) for q in (self.store.user_prices.get(c["uid"]) or {}).values()]
        book = PriceBook(list(self.store.__dict__.setdefault("price_quotes", {}).values()) + mine)
        try:
            req = MealPlanRequest(today=_d.today(), days=int(b.get("days", 7)), allergens=tuple(sorted(set(b.get("allergens", ())) | set(prof.get("allergens") or ()))),
                                  excluded_food_ids=tuple(b.get("excluded_food_ids", ())), diet_required=tuple(sorted(set(b.get("diet_required", ())) | set(prof.get("diet_required") or ()))),
                                  max_cook_minutes=b.get("max_cook_minutes"), weekly_budget=b.get("weekly_budget"), currency=b.get("currency"),
                                  region=b.get("region"), pantry=tuple(b.get("pantry", ())), allow_unreviewed=bool(self.rule_set.allow_unreviewed_content))
        except (TypeError, ValueError):
            raise ValidationFailed("meal_plan_request")
        res = plan_week(req, n, foods, recipes, book)
        d = _plain(res)
        d["safety_decision_id"] = pub("decision", res.safety_decision_id) if res.safety_decision_id else None
        if mine:
            d["labels"] = list(d.get("labels", [])) + ["user_entered_prices"]
        return d

    # ------------------------------------------------------------------ foods / recipes (browse), meal log, water, prices, shopping state
    @staticmethod
    def _q1(c, k):
        return (c["query"].get(k) or [None])[0]

    def _page(self, c, rows):
        try:
            page, size = int(self._q1(c, "page") or 1), int(self._q1(c, "page_size") or 20)
        except ValueError:
            raise BadRequest("pagination")
        if page < 1 or not 1 <= size <= 100:
            raise BadRequest("pagination")
        out = {"count": len(rows), "results": rows[(page - 1) * size: page * size]}
        if page * size < len(rows):
            out["next"] = f"?page={page + 1}&page_size={size}"
        return out

    def _avoid(self, c):
        from nutrition_engine.food import ALLERGENS
        raw = self._q1(c, "avoid_allergens")
        av = [x for x in (raw or "").split(",") if x]
        if any(x not in ALLERGENS for x in av):
            raise BadRequest("avoid_allergens")
        return av

    def _food_filters(self, c):
        from nutrition_engine.food import DIET_TAGS
        diet = self._q1(c, "diet") or ""
        if diet and diet not in DIET_TAGS:
            raise BadRequest("diet")
        return diet

    def op_api_food_001(self, c):
        from nutrition_engine import catalog_view as cv
        diet = self._food_filters(c)
        rows = cv.search_foods(self.store.__dict__.setdefault("foods", {}), bool(self.rule_set.allow_unreviewed_content), self._q1(c, "q") or "",
                               self._q1(c, "category") or "", diet, self._avoid(c))
        return self._page(c, [cv.food_summary(f) for f in rows])

    def op_api_food_002(self, c):
        from nutrition_engine import catalog_view as cv
        f = self.store.__dict__.setdefault("foods", {}).get(c["food_id"])
        if f is None or not cv.visible(f.status, bool(self.rule_set.allow_unreviewed_content)):
            raise NotFound()
        return cv.food_detail(f)

    def op_api_rec_001(self, c):
        from nutrition_engine import catalog_view as cv
        diet = self._food_filters(c)
        slot, mm = self._q1(c, "slot") or "", self._q1(c, "max_minutes")
        if slot and slot not in ("breakfast", "lunch", "dinner", "snack"):
            raise BadRequest("slot")
        try:
            mm = int(mm) if mm is not None else None
        except ValueError:
            raise BadRequest("max_minutes")
        foods = self.store.__dict__.setdefault("foods", {})
        rows = cv.search_recipes(self.store.__dict__.setdefault("recipes", {}).values(), foods, bool(self.rule_set.allow_unreviewed_content), self._q1(c, "q") or "", slot, diet, mm, self._avoid(c))
        return self._page(c, [cv.recipe_summary(r, foods) for r in rows])

    def op_api_rec_002(self, c):
        from nutrition_engine import catalog_view as cv
        foods = self.store.__dict__.setdefault("foods", {})
        r = self.store.__dict__.setdefault("recipes", {}).get(c["recipe_id"])
        if r is None or not cv.recipe_is_servable(r, foods, bool(self.rule_set.allow_unreviewed_content)):
            raise NotFound()
        return cv.recipe_detail(r, foods)

    # --- nutrition tracking (health-data consent + a nutrition result that is OK; REFER/BLOCKED users get no calorie tracking)
    def _nut_ok(self, uid):
        self._need_consent(uid)
        n = self._nut_result(uid)
        if n is None:
            raise NotFound("nutrition_profile")
        if n.status != "OK":
            raise Conflict("nutrition_unavailable")
        return n

    def _day_arg(self, raw):
        if raw is None or raw == "":
            return date.today().toordinal()
        try:
            d = date.fromisoformat(raw)
        except (TypeError, ValueError):
            raise BadRequest("date")
        if d > date.today() or (date.today() - d).days > 90:
            raise BadRequest("date")                                      # no future entries; history window 90 days
        return d.toordinal()

    def _meal_out(self, uid, e):
        prof = self.store.__dict__.get("nutrition_profiles", {}).get(uid) or {}
        mine = set(prof.get("allergens") or ())
        alert = None
        if e.source == "catalog" and mine and (mine & set(e.allergens) or not e.allergens_known):
            alert = {"allergens": sorted(mine & set(e.allergens)), "unknown": not e.allergens_known}
        out = {"id": pub("meal", e.id), "date": date.fromordinal(e.day).isoformat(), "slot": e.slot or "snack", "name": e.name, "source": e.source,
               "missing_nutrients": list(e.missing), "allergens": list(e.allergens), "allergens_known": e.allergens_known, "review_status": e.review_status, "allergen_alert": alert}
        for k in ("kcal", "protein_g", "carbs_g", "fat_g", "amount", "food_id", "recipe_id", "name_fa"):
            v = getattr(e, k)
            if v is not None:
                out[k] = round(v, 1) if isinstance(v, float) else v
        return out

    _MEAL_KEYS = {"slot", "date", "food_id", "grams", "recipe_id", "servings", "name", "kcal", "protein_g", "carbs_g", "fat_g"}

    @staticmethod
    def _num(v, lo, hi):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo < v <= hi:
            raise ValidationFailed("amount")
        return float(v)

    def op_api_nut_004(self, c):
        from nutrition_engine import catalog_view as cv
        from nutrition_engine.recipes import nutrition_per_serving, recipe_allergens
        uid, b = c["uid"], c["body"]
        self._nut_ok(uid)
        self._strict(b, self._MEAL_KEYS, "meal")
        if b.get("slot") not in ("breakfast", "lunch", "dinner", "snack"):
            raise ValidationFailed("slot")
        day = self._day_arg(b.get("date"))
        kinds = [k for k in ("food_id", "recipe_id", "name") if k in b]
        if len(kinds) != 1:
            raise ValidationFailed("exactly_one_source")
        allow = bool(self.rule_set.allow_unreviewed_content)
        foods = self.store.__dict__.setdefault("foods", {})
        if kinds[0] == "food_id":
            f = foods.get(b["food_id"]) if isinstance(b["food_id"], str) else None
            if f is None or not cv.visible(f.status, allow):
                raise NotFound()
            g = self._num(b.get("grams"), 0, 3000)
            nutr = {k: v * g / 100.0 for k, v in f.per_100g.items()}
            e = self.nlog.add_catalog_meal(uid, b["slot"], nutr, [k for k in cv.SUMMARY_NUTRIENTS if k not in f.per_100g], f.name_en, food_id=f.id, amount=g,
                                           allergens=f.allergens, allergens_known=f.allergens_known, review_status=cv.food_label(f), name_fa=f.name_fa, day=day)
        elif kinds[0] == "recipe_id":
            r = self.store.__dict__.setdefault("recipes", {}).get(b["recipe_id"]) if isinstance(b["recipe_id"], str) else None
            if r is None or not cv.recipe_is_servable(r, foods, allow):
                raise NotFound()
            sv = self._num(b.get("servings"), 0, 20)
            per, missing = nutrition_per_serving(r, foods)
            al, known = recipe_allergens(r, foods)
            e = self.nlog.add_catalog_meal(uid, b["slot"], {k: v * sv for k, v in per.items()}, [m for m in missing if m in cv.SUMMARY_NUTRIENTS], r.name_en, recipe_id=r.id, amount=sv,
                                           allergens=sorted(al), allergens_known=known, review_status=cv.recipe_label(r, foods), name_fa=r.name_fa, day=day)
        else:
            e = self.nlog.add_meal(uid, b["name"], b.get("kcal"), b.get("protein_g"), b.get("carbs_g"), b.get("fat_g"), day=day)
            e = dataclasses.replace(e, slot=b["slot"])
            self.store.meals[uid][-1] = e
        return self._meal_out(uid, e)

    def op_api_nut_005(self, c):
        uid = c["uid"]
        self._nut_ok(uid)
        day = self._day_arg(self._q1(c, "date"))
        return {"date": date.fromordinal(day).isoformat(), "meals": [self._meal_out(uid, e) for e in self.nlog.meals_on(uid, day)]}

    def op_api_nut_006(self, c):
        uid = c["uid"]
        self._need_consent(uid)                                          # deleting own entries stays possible for every user, including REFER profiles
        mid = resolve("meal", c["meal_id"], [e.id for e in self.store.meals.get(uid, [])])
        self.nlog.delete_meal(uid, mid)
        return {"message": "deleted"}

    def op_api_nut_007(self, c):
        uid, b = c["uid"], c["body"]
        self._need_consent(uid)
        self._strict(b, {"ml", "date"}, "water")
        day = self._day_arg(b.get("date"))
        self.nlog.add_water(uid, b.get("ml"), day=day)
        return {"date": date.fromordinal(day).isoformat(), "water_ml": sum(w["ml"] for w in self.store.water.get(uid, []) if w["day"] == day)}

    def op_api_nut_008(self, c):
        uid = c["uid"]
        n = self._nut_ok(uid)
        day = self._day_arg(self._q1(c, "date"))
        s = self.nlog.day_summary(uid, day=day, estimate=None)
        s.pop("vs_estimate", None)
        s["date"] = date.fromordinal(s.pop("day")).isoformat()
        s["targets"] = {"tdee": list(n.tdee) if n.tdee else None, "macros": {k: list(v) for k, v in (n.macros or {}).items()} or None,
                        "water_ml": list(n.water_ml) if n.water_ml else None}
        s["uncertainty"], s["labels"] = n.uncertainty, list(n.labels)
        return s

    # --- user-entered prices (budget). Never invented: only what the user typed, labelled `user_entered`, expiring like every quote.
    @staticmethod
    def _user_quote(q):
        from nutrition_engine import PriceQuote
        return PriceQuote(q["food_id"], q["region"], q["currency"], q["price_per_kg"], date.fromisoformat(q["observed_on"]), "user_entered", "user_reported")

    def op_api_nut_009(self, c):
        return {"prices": [{**q, "source": "user_entered"} for q in sorted((self.store.user_prices.get(c["uid"]) or {}).values(), key=lambda q: q["food_id"])]}

    def op_api_nut_010(self, c):
        import re as _re
        uid, b = c["uid"], c["body"]
        self._strict(b, {"food_id", "price_per_kg", "currency", "region"}, "price")
        if not isinstance(b.get("food_id"), str) or b["food_id"] not in self.store.__dict__.setdefault("foods", {}):
            raise NotFound()
        p = b.get("price_per_kg")
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 < p <= 1e9:
            raise ValidationFailed("price_per_kg")
        if not isinstance(b.get("currency"), str) or not _re.fullmatch(r"[A-Z]{3}", b["currency"]) or not isinstance(b.get("region"), str) or not _re.fullmatch(r"[A-Za-z0-9-]{2,16}", b["region"]):
            raise ValidationFailed("currency/region")
        row = {"food_id": b["food_id"], "price_per_kg": float(p), "currency": b["currency"], "region": b["region"], "observed_on": date.today().isoformat()}
        mine = dict(self.store.user_prices.get(uid) or {})
        mine[b["food_id"]] = row
        self.store.user_prices[uid] = mine
        return {**row, "source": "user_entered"}

    def op_api_nut_011(self, c):
        uid = c["uid"]
        mine = dict(self.store.user_prices.get(uid) or {})
        if c["food_id"] not in mine:
            raise NotFound()
        del mine[c["food_id"]]
        self.store.user_prices[uid] = mine
        return {"message": "deleted"}

    def op_api_nut_012(self, c):
        return {"checked": list(self.store.shopping_state.get(c["uid"]) or [])}

    def op_api_nut_013(self, c):
        b = c["body"]
        self._strict(b, {"checked"}, "shopping_state")
        v = b.get("checked")
        if not isinstance(v, list) or len(v) > 300 or any(not isinstance(x, str) or not 1 <= len(x) <= 64 for x in v) or len(set(v)) != len(v):
            raise ValidationFailed("checked")
        self.store.shopping_state[c["uid"]] = list(v)
        return {"checked": list(v)}

    # --- progression (explainable, deterministic; suggestions only, never auto-applied and never overriding the Safety Core)
    def op_api_wo_005(self, c):
        from workout_engine.progression import SessionPerf, SetLog, decide
        uid = c["uid"]
        if not self.store.plans.get(uid):
            raise NotFound()
        if not self._decision_obj(uid).status.permits_content:
            raise Conflict("safety_blocked")
        cur = self.w.current(uid)["result"]
        flags = cur.flags
        items, seen = [], set()
        for day in cur.days:
            for e in day.exercises:
                if e.code in seen:
                    continue
                seen.add(e.code)
                hist = []
                for w in sorted(self.store.workout_sessions.values(), key=lambda x: x["start"]):
                    if w["user"] != uid or not w["finished"]:
                        continue
                    sets = tuple(SetLog(l["reps"], l["load_kg"], l["rpe"]) for l in w["logs"] if l["code"] == e.code and not l.get("skipped") and l["reps"] > 0)
                    if sets or any(l["code"] == e.code for l in w["logs"]):
                        hist.append(SessionPerf(w["start"], sets, e.sets, e.reps_min, e.reps_max, bool(sets), w.get("aborted_reason") == "pain", w.get("perceived_difficulty")))
                rec = self.records.get(e.code)
                eq = next((k for k in ("barbell", "dumbbell", "machine") if rec and k in rec.equipment), "other")
                d = decide(hist, flags, eq, self.w.cfg)
                last = next((x for x in reversed(hist) if x.sets), None)
                item = {"exercise_id": pub("ex", e.code), "action": d.action, "reasons": list(d.reasons), "flags": list(d.flags), "confidence": d.confidence,
                        "sessions_considered": len(hist)}
                if last:
                    item["last_load_kg"], item["last_reps"] = last.sets[-1].load_kg, last.sets[-1].reps
                for k in ("new_load_kg", "target_reps", "factor"):
                    if k in d.params:
                        item[k] = d.params[k]
                items.append(item)
        return {"items": items, "note": "suggestions_only"}

    def _explain(self, c):
        from safety_core.explain import explain
        return explain(self.w.gate.evaluate(self._request_for(c["uid"])), "fa")

    # ------------------------------------------------------------------ WSGI
    def __call__(self, environ, start_response):
        method, path = environ["REQUEST_METHOD"], environ["PATH_INFO"]
        if method == "GET" and path == "/":
            html = (pathlib.Path(__file__).parent / "static" / "index.html").read_bytes()
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(html))),
                                      ("X-Content-Type-Options", "nosniff"), ("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")])
            return [html]
        try:
            tx = getattr(self.store, "transaction", None)
            with (tx() if tx else contextlib.nullcontext()):        # persistent stores: one atomic unit per request; unexpected error => rollback
                return self._dispatch(environ, start_response, method, path)
        except Exception:  # noqa: BLE001  never leak internals; the message is generic by design
            return self._err(start_response, 500, "internal_error")

    def _dispatch(self, environ, start_response, method, path):
        n = int(environ.get("CONTENT_LENGTH") or 0)
        if n > 100_000:
            return self._err(start_response, 413, "too_large")
        raw = environ["wsgi.input"].read(n) if n else b""
        path_matched = False
        for m, rx, fn, auth, op in self.routes:
            mt = rx.match(path)
            if not mt:
                continue
            path_matched = True
            if m != method:
                continue
            try:
                body = json.loads(raw) if raw else {}
            except (ValueError, UnicodeDecodeError):
                return self._err(start_response, self._pick(op, 400, 422), "bad_json")
            ctx = {"body": body, **mt.groupdict(), "query": parse_qs(environ.get("QUERY_STRING", "")), "ua": environ.get("HTTP_USER_AGENT", "")[:200]}
            try:
                if auth:
                    cookies = SimpleCookie(environ.get("HTTP_COOKIE", ""))
                    h = environ.get("HTTP_AUTHORIZATION", "")
                    bearer = h[7:] if h.startswith("Bearer ") else ""
                    ctx["token"] = bearer or (cookies["sessionid"].value if "sessionid" in cookies else "")
                    ctx["uid"] = self.id.authenticate(ctx["token"])
                    if not bearer and method not in ("GET", "HEAD", "OPTIONS"):          # ambient-cookie auth needs CSRF; bearer does not
                        tok = environ.get("HTTP_X_CSRFTOKEN", "")
                        if "csrftoken" not in cookies or not tok or not hmac.compare_digest(tok, cookies["csrftoken"].value):
                            return self._err(start_response, 403, "csrf_failed")
                if op is not None and op.request_schema:
                    v = self.contract.violations(op.request_schema, body)
                    if v:
                        return self._err(start_response, self._pick(op, 400, 422), "validation_failed", {"fields": [{"path": p, "rule": r} for p, r in v]})
                out = fn(ctx)
                rep = out if isinstance(out, Reply) else Reply(out)
                return self._send(start_response, rep.status or (op.success_status if op else 200), rep.body, rep.headers)
            except SafetyBlocked as e:                          # non-contract routes only
                return self._err(start_response, e.http, e.code, {"status": e.status, "reasons": list(e.reasons)})
            except NeedsContent as e:
                return self._err(start_response, self._pick(op, 422, 400), e.code, {"reasons": list(e.reasons), "omissions": list(e.omissions)})
            except AppError as e:
                st = 409 if e.http == 428 else e.http
                if isinstance(e, ValidationFailed):
                    st = self._pick(op, 422, 400)
                return self._err(start_response, st, e.code, {"reason": e.detail} if e.detail and e.detail != e.code else None)
        return self._err(start_response, 405 if path_matched else 404, "not_found")

    @staticmethod
    def _pick(op, preferred, other):
        """Validation failures use whichever of 400/422 the operation declares (preferred first)."""
        if op is None or preferred in op.declared:
            return preferred
        return other if other in op.declared else preferred

    def _err(self, start, status, code, details=None):
        body = {"code": code, "message": MESSAGES.get(code, "Error."), "request_id": str(uuid.uuid4())}
        if details:
            body["details"] = details
        return self._send(start, status, body, [])

    @staticmethod
    def _send(start, code, obj, headers):
        data = json.dumps(obj, ensure_ascii=False).encode()
        start(f"{code} X", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(data))),
                            ("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")] + headers)
        return [data]

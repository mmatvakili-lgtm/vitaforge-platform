"""Test harness: calls the WSGI app and validates EVERY exchange against the OpenAPI contract as it happens."""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app_services.store import InMemoryStore
from contract.spec import Operation, contract
from devserver.app import SCREENING, App
from devserver.demo_catalog import demo_catalog
from safety_core.models import RuleSet

PASSWORD = "Str0ngPassw0rd"
DOB = "1990-05-17"


@dataclass
class Exchange:
    op: Optional[Operation]
    method: str
    path: str
    status: int
    body: Any
    headers: Dict[str, str]
    problems: List[str]
    label: str = ""


class Harness:
    def __init__(self, dev: bool = True, allow: bool = True, mail=None, rule_kwargs: Optional[dict] = None, store=None, telegram=None):
        self.c = contract()
        s = store if store is not None else InMemoryStore()
        s.catalog = demo_catalog()
        s.relations = {c: [("demo_lunge_b" if "lunge" not in c else "demo_squat_b", "alternative")] for c in s.catalog}   # DEMO only
        rs = RuleSet(version=0, status="t", screening_questions=SCREENING, allow_unreviewed_content=allow, **(rule_kwargs or {}))
        from mailer.runtime import capture_runtime
        from tgverify import capture_runtime as tg_capture
        self.tg = telegram or tg_capture()
        self.app = App(s, rs, dev, mail or capture_runtime(s, "harness-secret-0123456789abcdef0123456789"), telegram=self.tg)
        self.store = s
        self.log: List[Exchange] = []
        self._rx = [(op, re.compile("^/api/v1" + re.sub(r"\{\w+\}", r"[^/]+", op.path) + "$")) for op in self.c.ops]

    def op_for(self, method: str, path: str) -> Optional[Operation]:
        p = path.split("?")[0]
        return next((op for op, rx in self._rx if op.method == method and rx.match("/api/v1" + p)), None)

    def call(self, method: str, path: str, body: Any = None, token: Optional[str] = None, raw: Optional[bytes] = None, label: str = "",
             headers: Optional[Dict[str, str]] = None, check: bool = True) -> Exchange:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        env = {"REQUEST_METHOD": method, "PATH_INFO": "/api/v1" + path.split("?")[0], "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
               "CONTENT_LENGTH": str(len(data)), "wsgi.input": io.BytesIO(data), "HTTP_USER_AGENT": "contract-test"}
        if token:
            env["HTTP_AUTHORIZATION"] = "Bearer " + token
        for k, v in (headers or {}).items():
            env["HTTP_" + k.upper().replace("-", "_")] = v
        out: Dict[str, Any] = {}
        res = b"".join(self.app(env, lambda st, h: out.update(status=int(st.split()[0]), headers=h)))
        hdrs: Dict[str, str] = {}
        for k, v in out["headers"]:
            hdrs[k] = (hdrs[k] + "\n" + v) if k in hdrs else v
        parsed = json.loads(res) if res else None
        op = self.op_for(method, path)
        problems: List[str] = []
        if check and op is not None:
            problems = self.c.check_response(op, out["status"], parsed, hdrs.get("Content-Type", ""))
        ex = Exchange(op, method, path, out["status"], parsed, hdrs, problems, label)
        self.log.append(ex)
        return ex

    # -- convenience
    def register(self, email: str, dob: str = DOB, role: Optional[str] = None, **kw) -> str:
        r = self.call("POST", "/auth/register", {"email": email, "password": PASSWORD, "date_of_birth": dob, "language": "fa"}, **kw)
        assert r.status == 201, (r.status, r.body)
        if role:
            self.store.users[self.store.by_email[email]]["role"] = role
        return email

    def login(self, email: str, role: Optional[str] = None) -> str:
        if email not in self.store.by_email:
            self.register(email, role=role)
        elif role:
            self.store.users[self.store.by_email[email]]["role"] = role
        if not self.store.users[self.store.by_email[email]]["verified"]:
            self.verify_by_mail(email)                                # the real flow: captured message -> POST /auth/verify
        r = self.call("POST", "/auth/login", {"identifier": email, "password": PASSWORD})
        assert r.status == 200, (r.status, r.body)
        m = re.search(r"sessionid=([^;]+)", r.headers["Set-Cookie"])
        return m.group(1)

    def tg_link(self, email: str, password: Optional[str] = None):
        """Request a Telegram verification link (real endpoint); returns (response, token or None)."""
        r = self.call("POST", "/auth/telegram/link", {"identifier": email, "password": password or PASSWORD})
        tok = r.body["deep_link"].split("start=")[1] if r.status == 200 else None
        return r, tok

    def tg_start(self, tg_id: int, token: str, secret: Optional[str] = None, text: Optional[str] = None):
        """What Telegram does when the user presses Start: POST the Update to the webhook with the secret header."""
        upd = {"update_id": 1, "message": {"message_id": 1, "from": {"id": tg_id, "is_bot": False}, "chat": {"id": tg_id, "type": "private"},
                                           "text": text if text is not None else "/start " + token}}
        return self.call("POST", "/telegram/webhook", upd, headers={"X-Telegram-Bot-Api-Secret-Token": secret or self.tg.webhook_secret})

    def verify_by_telegram(self, email: str, tg_id: int):
        r, tok = self.tg_link(email)
        assert r.status == 200, r.body
        r = self.tg_start(tg_id, tok)
        assert r.status == 200, r.body

    def captured(self, email: str, kind: str):
        return self.app.mail.sender.latest(email, kind)

    def verify_by_mail(self, email: str) -> None:
        row = self.captured(email, "verification")
        assert row, "no captured verification message"
        r = self.call("POST", "/auth/verify", {"identifier": email, "code": row["secret"]})
        assert r.status == 200, (r.status, r.body)

    def grant_consent(self, token: str) -> None:
        docs = self.call("GET", "/consents/documents", token=token).body
        d = next(x for x in docs if x["type"] == "health_data")
        assert self.call("POST", "/consents", {"document_id": d["id"], "granted": True}, token=token).status == 201

    def onboard(self, token: str, age: int = 30, days: int = 3, level: str = "beginner", equipment: Optional[list] = None, consent: bool = True) -> None:
        steps = [(1, {"age": age}), (2, {"goal": "strength", "level": level}), (3, {"days_per_week": days, "session_minutes": 90}),
                 (4, {"equipment": equipment or []})]
        for n, a in steps:
            r = self.call("PUT", f"/onboarding/steps/{n}", {"answers": a}, token=token)
            assert r.status == 200, (n, r.status, r.body)
        if consent:
            self.grant_consent(token)
        self.call("POST", "/health/screening", {"screening_version": 1, "answers": {q: False for q in SCREENING}}, token=token)

    @property
    def problems(self) -> List[Tuple[str, str, int, List[str]]]:
        return [(e.op.id if e.op else "?", f"{e.method} {e.path}", e.status, e.problems) for e in self.log if e.problems]

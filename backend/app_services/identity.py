"""Identity: register / login / sessions. scrypt hashing, lockout, opaque session tokens (hash stored)."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets

from .errors import AuthFailed, Conflict, Locked, NotFound, ValidationFailed

MAX_FAILS = 5
LOCK_SECONDS = 15 * 60
SESSION_TTL = 14 * 24 * 3600                 # sessions expire; no eternal tokens
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, salt, dk = stored.split("$")
        cand = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
        return hmac.compare_digest(cand.hex(), dk)
    except Exception:  # noqa: BLE001
        return False


def _token_hash(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


class IdentityService:
    def __init__(self, store, clock):
        self.s, self.clock = store, clock          # clock() -> int seconds (UTC)

    def register(self, email: str, password: str, locale: str = "fa", dob=None) -> str:
        email = (email or "").strip().lower()
        if not EMAIL.match(email):
            raise ValidationFailed("email")
        if len(password or "") < 10 or password.lower() == password or not re.search(r"\d", password):
            raise ValidationFailed("password")
        if locale not in ("fa", "en"):
            raise ValidationFailed("locale")
        if email in self.s.by_email:
            raise Conflict("email")                   # NOTE: API layer must answer generically to avoid enumeration
        uid = self.s.new_id("usr")
        self.s.users[uid] = {"id": uid, "email": email, "pw": hash_password(password), "locale": locale,
                             "verified": False, "dob": dob, "fails": 0, "locked_until": 0, "role": "user", "plan": "free"}
        self.s.by_email[email] = uid
        return uid

    def verify_email(self, uid: str):
        self._user(uid)["verified"] = True

    def login(self, email: str, password: str, device: str = "") -> str:
        uid = self.s.by_email.get((email or "").strip().lower())
        u = self.s.users.get(uid) if uid else None
        now = self.clock()
        if u and u["locked_until"] > now:
            raise Locked()
        ok = verify_password(password or "", u["pw"]) if u else (verify_password("x", hash_password("y")) and False)
        if not u or not ok:
            if u:
                u["fails"] += 1
                if u["fails"] >= MAX_FAILS:
                    u["locked_until"], u["fails"] = now + LOCK_SECONDS, 0
            raise AuthFailed()                         # identical error for unknown user / wrong password
        if not u["verified"]:
            raise AuthFailed("unverified")
        u["fails"] = 0
        token = secrets.token_urlsafe(32)
        sid = self.s.new_id("ses")
        self.s.sessions[_token_hash(token)] = {"id": sid, "user": u["id"], "device": device, "created": now, "exp": now + SESSION_TTL,
                                               "revoked": False}
        return token

    @staticmethod
    def _th(token: str) -> str:
        return _token_hash(token or "")

    def authenticate(self, token: str) -> str:
        s = self.s.sessions.get(_token_hash(token or ""))
        if not s or s["revoked"] or self.clock() >= s.get("exp", 0):
            raise AuthFailed()
        s["seen"] = self.clock()
        return s["user"]

    def session_of(self, token: str) -> dict:
        self.authenticate(token)
        return self.s.sessions[_token_hash(token)]

    def logout(self, token: str):
        s = self.s.sessions.get(_token_hash(token or ""))
        if s:
            s["revoked"] = True

    def list_sessions(self, uid: str):
        now = self.clock()
        return [{"id": s["id"], "device": s["device"], "created": s["created"], "seen": s.get("seen", s["created"]), "token_hash": h} for h, s in self.s.sessions.items()
                if s["user"] == uid and not s["revoked"] and now < s.get("exp", 0)]

    def revoke_session(self, uid: str, session_id: str):
        for s in self.s.sessions.values():
            if s["id"] == session_id and s["user"] == uid:
                s["revoked"] = True
                return
        raise NotFound()

    def _user(self, uid):
        if uid not in self.s.users:
            raise NotFound()
        return self.s.users[uid]

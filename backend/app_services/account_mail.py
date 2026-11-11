"""Account e-mail flows on the persistent outbox: verification (code), resend, password reset. Public answers never depend on whether an address exists."""
from __future__ import annotations

from mailer import tokens
from mailer.outbox import Outbox

from .errors import BadRequest, Gone, TooManyRequests

COOLDOWN_S = 60
MAX_PER_HOUR = 5


class AccountMail:
    def __init__(self, store, outbox: Outbox, more, identity, secret: str, clock):
        self.s, self.ob, self.m, self.id, self.secret, self.clock = store, outbox, more, identity, secret, clock
        store.__dict__.setdefault("mail_limits", {})
        self.fresh: list = []                                        # outbox ids created in this request (for inline processing)

    # ---- issuing
    def issue_verification(self, uid: str):
        u, now = self.s.users[uid], self.clock()
        nonce = tokens.new_nonce()
        code = tokens.derive_code(self.secret, uid, nonce)
        exp = now + tokens.VERIFY_TTL
        self.s.verification[uid] = {"hash": tokens.digest(code), "exp": exp, "attempts": 0, "nonce": nonce}   # replaces (= invalidates) any earlier code
        self.fresh.append(self.ob.enqueue("verification", uid, u["email"], u["locale"], nonce, exp))

    def resend_verification(self, email: str):
        email = (email or "").strip().lower()
        self._limit("verify", email)
        uid = self.s.by_email.get(email)
        if uid and not self.s.users[uid].get("verified"):
            self.issue_verification(uid)

    def request_reset(self, email: str):
        email = (email or "").strip().lower()
        self._limit("reset", email)
        nonce = tokens.new_nonce()
        token = tokens.derive_reset_token(self.secret, nonce)
        if self.m.request_reset(email, token):                       # False/None for unknown e-mail: same public answer, nothing queued
            uid = self.s.by_email[email]
            u = self.s.users[uid]
            self.fresh.append(self.ob.enqueue("password_reset", uid, email, u["locale"], nonce, self.clock() + tokens.RESET_TTL))

    # ---- verifying
    def verify(self, email: str, code: str):
        uid = self.s.by_email.get((email or "").strip().lower())
        rec = self.s.verification.get(uid) if uid else None
        if not rec:
            raise BadRequest("invalid_code")
        if rec["exp"] < self.clock():
            self.s.verification.pop(uid, None)
            raise Gone("code_expired")
        import hmac
        if not hmac.compare_digest(rec["hash"], tokens.digest(code)):
            rec["attempts"] = rec.get("attempts", 0) + 1
            if rec["attempts"] >= tokens.MAX_VERIFY_ATTEMPTS:
                self.s.verification.pop(uid, None)                   # brute force protection: a new code must be requested
            raise BadRequest("invalid_code")
        self.s.verification.pop(uid, None)                           # single use
        self.id.verify_email(uid)

    # ---- throttling (keyed by e-mail whether or not it exists => no enumeration)
    def _limit(self, kind: str, email: str):
        now = self.clock()
        key = tokens.digest(kind + "|" + email)
        rec = self.s.mail_limits.get(key) or {"t": []}
        recent = [t for t in rec["t"] if now - t < 3600]
        if recent and now - recent[-1] < COOLDOWN_S or len(recent) >= MAX_PER_HOUR:
            raise TooManyRequests("retry_later")
        self.s.mail_limits[key] = {"t": recent + [now]}

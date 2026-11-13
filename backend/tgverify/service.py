"""Token issue / consume. Tokens: 192-bit random, stored ONLY as SHA-256, single use, short lived, bound to one pending user.
Everything runs inside the request's atomic store transaction (row-locked load), so a token can be consumed at most once even under concurrency;
the Telegram id -> account mapping is a primary-keyed collection, so one Telegram id can never be linked to two accounts."""
from __future__ import annotations

import hashlib
import hmac
import secrets

from app_services.errors import TooManyRequests

TOKEN_TTL_S = 600
ISSUE_COOLDOWN_S = 20
ISSUE_PER_HOUR = 5
ATTEMPTS_PER_HOUR = 10


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class TelegramVerification:
    def __init__(self, store, clock):
        self.s, self.clock = store, clock
        for k in ("tg_tokens", "tg_links", "tg_limits"):
            store.__dict__.setdefault(k, {})

    # ---- issuing (requires proof of the pending account's password, checked by the caller)
    def issue(self, uid: str) -> tuple[str, int]:
        now = self.clock()
        rec = self.s.tg_limits.get("issue:" + uid) or {"t": []}
        recent = [t for t in rec["t"] if now - t < 3600]
        if (recent and now - recent[-1] < ISSUE_COOLDOWN_S) or len(recent) >= ISSUE_PER_HOUR:
            raise TooManyRequests("retry_later")
        self.s.tg_limits["issue:" + uid] = {"t": recent + [now]}
        for h in [h for h, r in self.s.tg_tokens.items() if r["user"] == uid]:
            self.s.tg_tokens.pop(h, None)                                   # a new link invalidates every earlier one
        token = secrets.token_urlsafe(24)
        exp = now + TOKEN_TTL_S
        self.s.tg_tokens[digest(token)] = {"user": uid, "exp": exp}
        return token, exp

    # ---- consuming (called by the bot webhook). Returns True/False only; the reason is never exposed.
    def consume(self, token: str, tg_id: int) -> bool:
        now = self.clock()
        lim_key = "att:" + digest(str(tg_id))
        lim = self.s.tg_limits.get(lim_key) or {"t": []}
        recent = [t for t in lim["t"] if now - t < 3600]
        if len(recent) >= ATTEMPTS_PER_HOUR:
            return False                                                     # throttled: no lookup, no side effect
        ok = self._try(token, tg_id, now)
        if not ok:
            self.s.tg_limits[lim_key] = {"t": recent + [now]}                # only failures count against the sender
        return ok

    def _try(self, token: str, tg_id: int, now: int) -> bool:
        h = digest(token or "")
        rec = None
        for k, v in self.s.tg_tokens.items():                               # constant-time comparison over hashes
            if hmac.compare_digest(k, h):
                rec = v
        if rec is None:
            return False
        if rec["exp"] < now:
            self.s.tg_tokens.pop(h, None)
            return False
        uid = rec["user"]
        u = self.s.users.get(uid)
        if not u or u.get("verified"):
            self.s.tg_tokens.pop(h, None)
            return False
        owner = self.s.tg_links.get(str(tg_id))
        if owner is not None and owner["user"] != uid:
            return False                                                     # this Telegram account already belongs to someone else; token stays unused
        self.s.tg_tokens.pop(h, None)                                        # single use
        self.s.tg_links[str(tg_id)] = {"user": uid, "linked_at": now}
        u["telegram"] = {"id": tg_id, "linked_at": now, "notifications": False}   # notifications need a separate, explicit opt-in
        u["verified"] = True
        self.s.__dict__.get("verification", {}).pop(uid, None)               # any pending e-mail code is void now
        self.s.audit.append({"kind": "telegram_verified", "user": uid, "at": now})
        return True

    # ---- consent for future notifications (nothing sends notifications yet)
    def set_notifications(self, uid: str, enabled: bool) -> dict:
        tg = self.s.users[uid].get("telegram")
        if not tg:
            return {"linked": False, "notifications": False}
        tg["notifications"] = bool(enabled)
        return {"linked": True, "notifications": tg["notifications"]}

    def status(self, uid: str) -> dict:
        tg = self.s.users[uid].get("telegram")
        return {"linked": bool(tg), "notifications": bool(tg and tg.get("notifications"))}

    def forget(self, uid: str):
        u = self.s.users.get(uid) or {}
        tg = u.get("telegram")
        if tg:
            self.s.tg_links.pop(str(tg["id"]), None)
        for h in [h for h, r in self.s.tg_tokens.items() if r["user"] == uid]:
            self.s.tg_tokens.pop(h, None)
        self.s.tg_limits.pop("issue:" + uid, None)

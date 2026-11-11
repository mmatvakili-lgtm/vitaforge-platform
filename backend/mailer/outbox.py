"""Durable e-mail outbox on the application store (PersistentStore => the real database; no new table, new KV collections `outbox`).

Lifecycle:   pending -> processing -> sent | captured | retry_scheduled -> processing -> ... -> failed | expired
  * claim():   under the record's row lock (select_for_update on PostgreSQL; SQLite serialises writers) the record is re-read, due-checked and moved to
               `processing` with a lease; a second worker therefore sees `processing` and skips it (no duplicate sends).
  * a worker that dies leaves `processing`; once the lease expires the record is reclaimable (the attempt was already counted).
  * transient errors => retry_scheduled with bounded exponential backoff; permanent errors or max attempts => failed.
  * past `expires_at` (= the token's expiry), or superseded/no longer needed => expired. No message is ever sent after its token is dead.
  * terminal states wipe the recipient and nonce (data minimisation). Only the nonce is stored while live; the code/token is re-derived at send time.
`sent` is set ONLY when the adapter reports `sent`; the capture adapter yields `captured`."""
from __future__ import annotations

import logging
import secrets
from typing import List, Optional

from . import tokens
from .ports import DeliveryError, MailSender

log = logging.getLogger("vitaforge.mail")

LIVE = ("pending", "retry_scheduled", "processing")
TERMINAL = ("sent", "captured", "failed", "expired")


class Outbox:
    def __init__(self, store, sender: MailSender, secret: str, clock, frontend_base_url: str, max_attempts: int = 6,
                 base_delay: int = 60, max_delay: int = 3600, lease: int = 300):
        self.s, self.sender, self.secret, self.clock = store, sender, secret, clock
        self.base_url = frontend_base_url.rstrip("/")
        self.max_attempts, self.base_delay, self.max_delay, self.lease = max_attempts, base_delay, max_delay, lease
        store.__dict__.setdefault("outbox", {})
        store.__dict__.setdefault("verification", {})
        store.__dict__.setdefault("reset_index", {})

    # ---- producers
    def enqueue(self, kind: str, user: str, to: str, locale: str, nonce: str, expires_at: int) -> str:
        now = self.clock()
        mid = secrets.token_hex(12)
        self.s.outbox[mid] = {"id": mid, "kind": kind, "user": user, "to": to, "locale": locale, "nonce": nonce, "status": "pending", "attempts": 0,
                              "created": now, "updated": now, "next_attempt": now, "lease_until": 0, "expires_at": expires_at, "error": ""}
        return mid

    # ---- consumers
    def due_ids(self) -> List[str]:
        now = self.clock()
        return [k for k, r in self.s.outbox.items()
                if (r["status"] in ("pending", "retry_scheduled") and r["next_attempt"] <= now) or (r["status"] == "processing" and r["lease_until"] <= now)]

    def claim(self, mid: str) -> Optional[dict]:
        r = self.s.outbox.get(mid)
        now = self.clock()
        if not r or r["status"] not in LIVE:
            return None
        if r["status"] == "processing" and r["lease_until"] > now:
            return None                                              # another worker owns it
        if r["status"] in ("pending", "retry_scheduled") and r["next_attempt"] > now:
            return None
        stale = self._stale(r, now)
        if stale:
            self._terminal(r, "expired", stale, now)
            return None
        if r["attempts"] >= self.max_attempts:                       # an interrupted last attempt
            self._terminal(r, "failed", "interrupted", now)
            return None
        r["status"], r["attempts"], r["lease_until"], r["updated"] = "processing", r["attempts"] + 1, now + self.lease, now
        return dict(r)

    def attempt(self, claimed: dict):
        """Network/IO step: touches NO store state. Returns (DeliveryResult|None, DeliveryError|None)."""
        try:
            return self._render_and_send(claimed), None
        except DeliveryError as e:
            return None, e

    def finish(self, mid: str, result, error: Optional[DeliveryError]) -> str:
        r = self.s.outbox[mid]
        now = self.clock()
        if error is None:
            self._terminal(r, result.status, "", now)                # "sent" only if the adapter said so; "captured" otherwise
        elif error.permanent or r["attempts"] >= self.max_attempts:
            self._terminal(r, "failed", error.code, now)
        else:
            delay = min(self.base_delay * 2 ** (r["attempts"] - 1), self.max_delay)
            r.update(status="retry_scheduled", next_attempt=now + delay, lease_until=0, updated=now, error=error.code)
            log.warning("mail outbox id=%s kind=%s status=retry_scheduled attempts=%d error=%s", mid, r["kind"], r["attempts"], error.code)
        return r["status"]

    def status_of(self, mid: str) -> str:
        r = self.s.outbox.get(mid)
        return r["status"] if r else "missing"

    def process_inline(self, mid: str) -> Optional[str]:
        """Single-transaction processing for adapters without a network (capture). Network adapters use claim/attempt/finish in separate transactions."""
        c = self.claim(mid)
        if not c:
            return None
        res, err = self.attempt(c)
        return self.finish(mid, res, err)

    # ---- internals
    def _stale(self, r: dict, now: int) -> str:
        if r["expires_at"] <= now:
            return "token_expired"
        u = self.s.users.get(r["user"])
        if not u:
            return "user_gone"
        if r["kind"] == "verification":
            v = self.s.verification.get(r["user"])
            if u.get("verified"):
                return "already_verified"
            if not v or v.get("nonce") != r["nonce"]:
                return "superseded"
        elif r["kind"] == "password_reset":
            tok = tokens.derive_reset_token(self.secret, r["nonce"])
            if self.s.reset_index.get(r["user"]) != tokens.digest(tok):
                return "superseded"
        return ""

    def _render_and_send(self, r: dict):
        if r["kind"] == "verification":
            return self.sender.send_verification(r["to"], tokens.derive_code(self.secret, r["user"], r["nonce"]), r["locale"])
        tok = tokens.derive_reset_token(self.secret, r["nonce"])
        return self.sender.send_password_reset(r["to"], tok, f"{self.base_url}/{r['locale']}/reset?token={tok}", r["locale"])

    def _terminal(self, r: dict, status: str, error: str, now: int):
        r.update(status=status, error=error, updated=now, lease_until=0, to="", nonce="")
        log.info("mail outbox id=%s kind=%s status=%s attempts=%d error=%s", r["id"], r["kind"], status, r["attempts"], error or "-")

    # ---- reporting (counts only)
    def counts(self) -> dict:
        out: dict = {}
        for r in self.s.outbox.values():
            out[r["status"]] = out.get(r["status"], 0) + 1
        return out

"""MailSender port: provider-independent delivery of the two account e-mails. Adapters implement `_deliver` only.

Delivery results are explicit: `sent` means an SMTP server accepted the message (it is NOT proof the recipient received it);
`captured` means a development adapter stored the message locally and NOTHING was delivered. `DeliveryResult.delivered` is True only for `sent`.
Logging never includes recipient addresses, tokens or codes."""
from __future__ import annotations

import dataclasses
import re
from typing import Optional

from . import templates

ADDRESS = re.compile(r"^[^@\s<>\"',;]+@[^@\s<>\"',;]+\.[^@\s<>\"',;]+$")


class DeliveryError(Exception):
    """`permanent=True`: retrying cannot help (bad recipient, rejected content). `code` is a short machine reason, never user data."""

    def __init__(self, code: str, permanent: bool = False):
        super().__init__(code)
        self.code, self.permanent = code, permanent


@dataclasses.dataclass(frozen=True)
class MailMessage:
    to: str
    subject: str
    text: str
    html: Optional[str] = None
    kind: str = "generic"          # verification | password_reset | test
    secret: str = ""               # code/token contained in the message; only the capture adapter ever keeps it


@dataclasses.dataclass(frozen=True)
class DeliveryResult:
    status: str                    # "sent" | "captured"
    provider: str
    delivered: bool


class MailSender:
    provider = "abstract"
    delivers_real_mail = False
    inline = False                 # True: the application may process the outbox in-request (capture only)

    def _deliver(self, msg: MailMessage) -> DeliveryResult:
        raise NotImplementedError

    def send(self, msg: MailMessage) -> DeliveryResult:
        if not ADDRESS.match(msg.to or ""):
            raise DeliveryError("invalid_recipient", permanent=True)
        return self._deliver(msg)

    def send_verification(self, to: str, code: str, locale: str) -> DeliveryResult:
        s, t, h = templates.verification(code, locale)
        return self.send(MailMessage(to, s, t, h, "verification", code))

    def send_password_reset(self, to: str, token: str, link: str, locale: str) -> DeliveryResult:
        s, t, h = templates.password_reset(link, locale)
        return self.send(MailMessage(to, s, t, h, "password_reset", token))


class DisabledSender(MailSender):
    """No provider configured: nothing is ever delivered and the outbox keeps messages (they expire with their tokens)."""
    provider = "disabled"

    def _deliver(self, msg):
        raise DeliveryError("provider_not_configured")

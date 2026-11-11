from __future__ import annotations

import smtplib
import ssl
import uuid
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import MutableMapping, Optional

from .ports import DeliveryError, DeliveryResult, MailMessage, MailSender


class CaptureSender(MailSender):
    """Development/test adapter. Stores messages (INCLUDING the code/token) in a local sink so a developer can read them. Delivers nothing:
    `delivered` is always False and the outbox status is `captured`, never `sent`. Refused outside DJANGO_DEBUG=true by mailer.config."""
    provider = "capture"
    inline = True

    def __init__(self, sink: MutableMapping):
        self.sink = sink

    def _deliver(self, msg: MailMessage) -> DeliveryResult:
        self.sink[uuid.uuid4().hex] = {"to": msg.to, "subject": msg.subject, "text": msg.text, "kind": msg.kind, "secret": msg.secret}
        return DeliveryResult("captured", self.provider, False)

    def latest(self, to: str, kind: str) -> Optional[dict]:
        rows = [v for v in self.sink.values() if v["to"] == to.strip().lower() and v["kind"] == kind]
        return rows[-1] if rows else None


class SmtpSender(MailSender):
    provider = "smtp"
    delivers_real_mail = True

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def _build(self, msg: MailMessage) -> EmailMessage:
        m = EmailMessage()
        m["From"] = formataddr((self.cfg["from_name"], self.cfg["from_address"]))
        m["To"] = msg.to
        m["Subject"] = msg.subject
        m["Date"] = formatdate(localtime=False)
        m["Message-ID"] = make_msgid(domain=self.cfg["from_address"].split("@")[-1])
        m.set_content(msg.text)
        if msg.html:
            m.add_alternative(msg.html, subtype="html")
        return m

    def _connect(self):
        c, t = self.cfg, self.cfg["timeout"]
        if c["security"] == "ssl":
            return smtplib.SMTP_SSL(c["host"], c["port"], timeout=t, context=ssl.create_default_context())
        s = smtplib.SMTP(c["host"], c["port"], timeout=t)
        if c["security"] == "starttls":
            s.starttls(context=ssl.create_default_context())
        return s

    def _deliver(self, msg: MailMessage) -> DeliveryResult:
        try:
            body = self._build(msg)
        except ValueError:
            raise DeliveryError("invalid_message", permanent=True)
        try:
            with self._connect() as s:
                if self.cfg["username"]:
                    s.login(self.cfg["username"], self.cfg["password"])
                s.send_message(body)
        except smtplib.SMTPRecipientsRefused:
            raise DeliveryError("recipient_refused", permanent=True)
        except smtplib.SMTPAuthenticationError:
            raise DeliveryError("smtp_auth_failed")                       # configuration problem: retried with backoff, never "sent"
        except smtplib.SMTPResponseException as e:
            raise DeliveryError(f"smtp_{e.smtp_code}", permanent=500 <= e.smtp_code < 600)
        except (smtplib.SMTPException, OSError):
            raise DeliveryError("smtp_unavailable")
        return DeliveryResult("sent", self.provider, True)

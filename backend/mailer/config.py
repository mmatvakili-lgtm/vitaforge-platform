"""Environment-based mail configuration (validated at start-up). Never contains defaults for credentials."""
from __future__ import annotations

from typing import Mapping

PROVIDERS = ("capture", "smtp", "disabled")


class MailConfigError(Exception):
    pass


def load_mail_config(env: Mapping[str, str], debug: bool) -> dict:
    provider = (env.get("MAIL_PROVIDER") or "").strip().lower()
    base = (env.get("FRONTEND_BASE_URL") or "http://localhost:3000").rstrip("/")
    if not provider:
        if not debug:
            raise MailConfigError("MAIL_PROVIDER is not set: SMTP is not configured (production requires MAIL_PROVIDER=smtp)")
        provider = "disabled"                                           # development default: nothing is delivered, and nothing pretends to be
    if provider not in PROVIDERS:
        raise MailConfigError("MAIL_PROVIDER must be one of " + ",".join(PROVIDERS))
    if not debug and provider != "smtp":
        raise MailConfigError(f"MAIL_PROVIDER={provider} is only allowed with DJANGO_DEBUG=true; production requires smtp")
    cfg = {"provider": provider, "frontend_base_url": base}
    if provider == "smtp":
        missing = [k for k in ("SMTP_HOST", "MAIL_FROM_ADDRESS") if not (env.get(k) or "").strip()]
        if missing:
            raise MailConfigError("SMTP is not configured; missing: " + ",".join(missing))
        sec = (env.get("SMTP_SECURITY") or "starttls").strip().lower()
        if sec not in ("starttls", "ssl", "none"):
            raise MailConfigError("SMTP_SECURITY must be starttls, ssl or none")
        if sec == "none" and not debug:
            raise MailConfigError("SMTP_SECURITY=none is not allowed in production")
        try:
            port = int(env.get("SMTP_PORT") or (465 if sec == "ssl" else 587))
            timeout = float(env.get("SMTP_TIMEOUT") or 10)
        except ValueError:
            raise MailConfigError("SMTP_PORT / SMTP_TIMEOUT must be numeric")
        user, pw = (env.get("SMTP_USERNAME") or "").strip(), env.get("SMTP_PASSWORD") or ""
        if bool(user) != bool(pw):
            raise MailConfigError("SMTP_USERNAME and SMTP_PASSWORD must be set together")
        if "@" not in env["MAIL_FROM_ADDRESS"]:
            raise MailConfigError("MAIL_FROM_ADDRESS must be an e-mail address")
        cfg["smtp"] = {"host": env["SMTP_HOST"].strip(), "port": port, "username": user, "password": pw, "security": sec, "timeout": timeout,
                       "from_address": env["MAIL_FROM_ADDRESS"].strip(), "from_name": (env.get("MAIL_FROM_NAME") or "VitaForge").strip()}
    return cfg


def build_sender(cfg: dict, captured_sink=None):
    from .adapters import CaptureSender, SmtpSender
    from .ports import DisabledSender
    if cfg["provider"] == "smtp":
        return SmtpSender(cfg["smtp"])
    if cfg["provider"] == "capture":
        if captured_sink is None:
            raise MailConfigError("capture adapter needs a sink")
        return CaptureSender(captured_sink)
    return DisabledSender()

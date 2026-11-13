"""Environment-based Telegram configuration, validated at start-up. No defaults for secrets. The bot token never appears in any message."""
from __future__ import annotations

import re
from typing import Mapping

PROVIDERS = ("live", "capture", "disabled")
USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
SECRET = re.compile(r"^[A-Za-z0-9_-]{16,256}$")          # the character set Telegram allows for webhook secret tokens
BOT_TOKEN = re.compile(r"^\d{5,20}:[A-Za-z0-9_-]{20,}$")


class TelegramConfigError(Exception):
    pass


def load_telegram_config(env: Mapping[str, str], debug: bool) -> dict:
    token = (env.get("TELEGRAM_BOT_TOKEN") or "").strip()
    user = (env.get("TELEGRAM_BOT_USERNAME") or "").strip().lstrip("@")
    secret = (env.get("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    provider = (env.get("TELEGRAM_PROVIDER") or "").strip().lower() or ("live" if token and user else "disabled")
    if provider not in PROVIDERS:
        raise TelegramConfigError("TELEGRAM_PROVIDER must be one of " + ",".join(PROVIDERS))
    if provider == "capture" and not debug:
        raise TelegramConfigError("TELEGRAM_PROVIDER=capture is only allowed with DJANGO_DEBUG=true")
    cfg = {"provider": provider, "username": user, "token": token, "webhook_secret": secret}
    if provider == "live":
        missing = [k for k, v in (("TELEGRAM_BOT_TOKEN", token), ("TELEGRAM_BOT_USERNAME", user), ("TELEGRAM_WEBHOOK_SECRET", secret)) if not v]
        if missing:
            raise TelegramConfigError("Telegram is not fully configured; missing: " + ",".join(missing))
        if not BOT_TOKEN.match(token):
            raise TelegramConfigError("TELEGRAM_BOT_TOKEN has an invalid format")
    if provider in ("live", "capture") and user and not USERNAME.match(user):
        raise TelegramConfigError("TELEGRAM_BOT_USERNAME is not a valid bot username")
    if secret and not SECRET.match(secret):
        raise TelegramConfigError("TELEGRAM_WEBHOOK_SECRET must be 16-256 characters of A-Z a-z 0-9 _ -")
    if provider == "capture" and not (user and secret):
        raise TelegramConfigError("capture mode needs TELEGRAM_BOT_USERNAME and TELEGRAM_WEBHOOK_SECRET")
    return cfg

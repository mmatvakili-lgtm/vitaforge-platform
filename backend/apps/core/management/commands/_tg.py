"""Shared helpers for the telegram_* commands (nothing here logs or prints the bot token)."""
import io
import json
import urllib.request

from django.core.management.base import CommandError


def deliver_to_app(update: dict, secret: str) -> int:
    """Feed one Update to the real webhook route in-process, exactly as Telegram's HTTPS POST would arrive."""
    from config.wsgi import _api_app
    data = json.dumps(update).encode()
    env = {"REQUEST_METHOD": "POST", "PATH_INFO": "/api/v1/telegram/webhook", "QUERY_STRING": "", "CONTENT_LENGTH": str(len(data)),
           "wsgi.input": io.BytesIO(data), "HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN": secret, "HTTP_USER_AGENT": "telegram-poll"}
    out = {}
    list(_api_app()(env, lambda st, h: out.update(status=int(st.split()[0]))))
    return out["status"]


def bot_api(token: str, method: str, payload: dict, timeout: float = 40.0) -> dict:
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:      # noqa: S310 (fixed https URL)
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001  never echo the URL (it contains the token)
        raise CommandError(f"Telegram API call {method} failed ({type(e).__name__}); check network access and TELEGRAM_BOT_TOKEN")


def live_cfg():
    from django.conf import settings
    cfg = settings.CFG["telegram"]
    if cfg["provider"] != "live":
        raise CommandError("Telegram is not live: set TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_USERNAME and TELEGRAM_WEBHOOK_SECRET")
    return cfg

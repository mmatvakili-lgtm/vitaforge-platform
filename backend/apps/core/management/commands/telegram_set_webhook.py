"""python manage.py telegram_set_webhook --url https://api.example.org      (PRODUCTION; needs a public HTTPS URL)
Registers <url>/api/v1/telegram/webhook with Telegram using TELEGRAM_WEBHOOK_SECRET as secret_token. `--delete` removes it.
NEEDS LOCAL VERIFICATION: requires a real bot and a public HTTPS host."""
from django.core.management.base import BaseCommand, CommandError

from ._tg import bot_api, live_cfg


class Command(BaseCommand):
    help = "Register or remove the Telegram webhook."

    def add_arguments(self, p):
        p.add_argument("--url")
        p.add_argument("--delete", action="store_true")

    def handle(self, *a, url, delete, **o):
        cfg = live_cfg()
        if delete:
            r = bot_api(cfg["token"], "deleteWebhook", {})
        else:
            if not url or not url.startswith("https://"):
                raise CommandError("--url must be a public https:// base URL")
            r = bot_api(cfg["token"], "setWebhook", {"url": url.rstrip("/") + "/api/v1/telegram/webhook", "secret_token": cfg["webhook_secret"],
                                                     "allowed_updates": ["message"], "max_connections": 10})
        self.stdout.write("ok" if r.get("ok") else "Telegram refused the request")

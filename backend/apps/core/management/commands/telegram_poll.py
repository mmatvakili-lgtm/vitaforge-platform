"""python manage.py telegram_poll        (LOCAL DEVELOPMENT, real bot, no public URL needed)
Long-polls Telegram getUpdates and hands every update to the same webhook route production uses. Removes any registered webhook first
(Telegram does not allow both). Needs outbound access to api.telegram.org and TELEGRAM_BOT_TOKEN/USERNAME/WEBHOOK_SECRET. Stop with Ctrl+C.
NEEDS LOCAL VERIFICATION: cannot be exercised without a real bot."""
from django.core.management.base import BaseCommand

from ._tg import bot_api, deliver_to_app, live_cfg


class Command(BaseCommand):
    help = "Poll Telegram for /start messages (development alternative to the webhook)."

    def handle(self, *a, **o):
        cfg = live_cfg()
        bot_api(cfg["token"], "deleteWebhook", {"drop_pending_updates": False})
        self.stdout.write(f"Polling as @{cfg['username']} ... (Ctrl+C to stop)")
        offset = None
        try:
            while True:
                r = bot_api(cfg["token"], "getUpdates", {"timeout": 25, "allowed_updates": ["message"], **({"offset": offset} if offset else {})})
                for u in r.get("result", []):
                    offset = u["update_id"] + 1
                    status = deliver_to_app(u, cfg["webhook_secret"])
                    self.stdout.write(f"update {u['update_id']} -> HTTP {status}")
        except KeyboardInterrupt:
            self.stdout.write("stopped")

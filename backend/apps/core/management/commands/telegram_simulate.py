"""python manage.py telegram_simulate --token <token-from-deep-link> --telegram-id 123456789      (DEV ONLY, no network)
Needs DJANGO_DEBUG=true and TELEGRAM_PROVIDER=capture (+ TELEGRAM_BOT_USERNAME, TELEGRAM_WEBHOOK_SECRET). Plays the role of Telegram: sends a
/start <token> update through the real webhook route. It still needs a genuine single-use token; the bot's reply is printed, NOT delivered."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Simulate pressing Start in the bot (development only)."

    def add_arguments(self, p):
        p.add_argument("--token", required=True)
        p.add_argument("--telegram-id", type=int, required=True)

    def handle(self, *a, token, telegram_id, **o):
        from django.conf import settings
        cfg = settings.CFG["telegram"]
        if cfg["provider"] != "capture" or not settings.DEBUG:
            raise CommandError("simulation needs DJANGO_DEBUG=true and TELEGRAM_PROVIDER=capture")
        from ._tg import deliver_to_app
        upd = {"update_id": 1, "message": {"message_id": 1, "from": {"id": telegram_id, "is_bot": False},
                                           "chat": {"id": telegram_id, "type": "private"}, "text": "/start " + token}}
        st = deliver_to_app(upd, cfg["webhook_secret"])
        self.stdout.write(f"webhook HTTP {st} (the verification result is shown by the app: sign in again; the bot reply is not delivered in capture mode)")

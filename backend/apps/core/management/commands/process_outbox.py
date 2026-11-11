"""python manage.py process_outbox [--loop --interval 15] [--limit 50]
Drains the persistent e-mail outbox through the configured provider (MAIL_PROVIDER). Safe to run several workers: messages are claimed under a row lock with a lease.
With MAIL_PROVIDER=disabled nothing can be delivered and the command says so. NEEDS LOCAL VERIFICATION against a real database."""
import time

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Deliver pending e-mails from the outbox."

    def add_arguments(self, p):
        p.add_argument("--loop", action="store_true")
        p.add_argument("--interval", type=int, default=15)
        p.add_argument("--limit", type=int, default=50)

    def handle(self, *a, loop, interval, limit, **o):
        from django.conf import settings

        from apps.core.kv_backend import DjangoBackend
        from mailer import Outbox, build_sender
        from mailer.worker import process_due
        from persistence import PersistentStore
        cfg = settings.CFG["mail"]
        store = PersistentStore(DjangoBackend())
        sender = build_sender(cfg, store.captured_mail)
        if sender.provider == "disabled":
            raise CommandError("MAIL_PROVIDER is not configured: nothing can be delivered (set MAIL_PROVIDER=smtp, see docs/PROJECT_STATE.md)")
        ob = Outbox(store, sender, settings.CFG["secret_key"], lambda: int(time.time()), cfg["frontend_base_url"])
        while True:
            res = process_due(store, ob, limit)
            if res:
                self.stdout.write(f"provider={sender.provider} " + " ".join(f"{k}={v}" for k, v in sorted(res.items())))
            if not loop:
                return
            time.sleep(interval)

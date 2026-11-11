"""python manage.py show_captured_mail [--to a@b.co]   (development only: MAIL_PROVIDER=capture and DJANGO_DEBUG=true)
Prints messages captured instead of being sent, so a developer can read the verification code / reset link. Nothing was delivered."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Show captured (NOT delivered) development e-mails."

    def add_arguments(self, p):
        p.add_argument("--to")

    def handle(self, *a, to, **o):
        from django.conf import settings

        from apps.core.kv_backend import DjangoBackend
        from persistence import PersistentStore
        if settings.CFG["mail"]["provider"] != "capture" or not settings.DEBUG:
            raise CommandError("capture mode is not active (MAIL_PROVIDER=capture with DJANGO_DEBUG=true)")
        store = PersistentStore(DjangoBackend())
        with store.transaction():
            for row in store.captured_mail.values():
                if to and row["to"] != to.strip().lower():
                    continue
                self.stdout.write(f"[CAPTURED, NOT DELIVERED] to={row['to']} kind={row['kind']} subject={row['subject']}\n{row['text']}\n")

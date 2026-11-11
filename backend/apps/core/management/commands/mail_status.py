"""python manage.py mail_status [--send-test you@example.org]
Reports the configured provider and outbox counts (no secrets, no addresses). --send-test performs ONE real SMTP delivery of a harmless test message
(only with MAIL_PROVIDER=smtp); success there is the only thing that justifies calling real e-mail delivery verified. NEEDS LOCAL VERIFICATION."""
import time

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Show mail provider and outbox status."

    def add_arguments(self, p):
        p.add_argument("--send-test")

    def handle(self, *a, send_test, **o):
        from django.conf import settings

        from apps.core.kv_backend import DjangoBackend
        from mailer import DeliveryError, MailMessage, Outbox, build_sender
        from persistence import PersistentStore
        cfg = settings.CFG["mail"]
        store = PersistentStore(DjangoBackend())
        sender = build_sender(cfg, store.captured_mail)
        ob = Outbox(store, sender, settings.CFG["secret_key"], lambda: int(time.time()), cfg["frontend_base_url"])
        with store.transaction():
            counts = ob.counts()
        self.stdout.write(f"provider={sender.provider} real_delivery_possible={sender.delivers_real_mail} outbox={counts or '{}'}")
        if sender.provider == "disabled":
            self.stdout.write("SMTP is NOT configured: set MAIL_PROVIDER=smtp (+ SMTP_HOST, MAIL_FROM_ADDRESS, credentials).")
        if send_test:
            if sender.provider != "smtp":
                raise CommandError("--send-test requires MAIL_PROVIDER=smtp")
            try:
                r = sender.send(MailMessage(send_test, "VitaForge SMTP test", "This is a VitaForge SMTP configuration test. No action is needed.", kind="test"))
            except DeliveryError as e:
                raise CommandError(f"SMTP test FAILED: {e.code}")
            self.stdout.write(f"SMTP test accepted by server (status={r.status}). Confirm receipt in the inbox before treating delivery as verified.")

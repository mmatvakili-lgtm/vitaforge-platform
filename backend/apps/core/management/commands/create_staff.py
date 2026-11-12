"""python manage.py create_staff --email a@b.co --password '...' --role admin|content_admin|exercise_reviewer|nutrition_reviewer|clinical_safety_reviewer
Creates a verified staff account through the same IdentityService the API uses (no separate password path). NEEDS LOCAL VERIFICATION."""
import time

from django.core.management.base import BaseCommand, CommandError

ROLES = ("admin", "content_admin", "exercise_reviewer", "nutrition_reviewer", "clinical_safety_reviewer", "professional")


class Command(BaseCommand):
    help = "Create a verified staff user."

    def add_arguments(self, p):
        p.add_argument("--email", required=True)
        p.add_argument("--password", required=True)
        p.add_argument("--role", required=True, choices=ROLES)

    def handle(self, *a, email, password, role, **o):
        from app_services.errors import AppError
        from app_services.identity import IdentityService
        from apps.core.kv_backend import DjangoBackend
        from persistence import PersistentStore
        store = PersistentStore(DjangoBackend())
        try:
            with store.transaction():
                ids = IdentityService(store, lambda: int(time.time()))
                uid = ids.register(email, password)
                ids.verify_email(uid)
                store.users[uid]["role"] = role
        except AppError as e:
            raise CommandError(f"could not create user: {e.code}") from e
        self.stdout.write(self.style.SUCCESS(f"created {role}: {email}"))

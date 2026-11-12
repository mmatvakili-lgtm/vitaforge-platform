"""python manage.py restore_db --in backup.json [--replace --yes]
Verifies the checksum before touching anything, then restores inside one transaction. Refuses a non-empty database unless --replace --yes is given.
Everyone must sign in again afterwards (sessions are not part of a backup). NEEDS LOCAL VERIFICATION against a real database."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore the persistent store from a backup file."

    def add_arguments(self, p):
        p.add_argument("--in", dest="src", required=True)
        p.add_argument("--replace", action="store_true")
        p.add_argument("--yes", action="store_true")

    def handle(self, *a, src, replace, yes, **o):
        from django.db import transaction

        from apps.core.kv_backend import DjangoBackend
        from persistence.backup import BackupError, restore_backup
        if replace and not yes:
            raise CommandError("--replace deletes all current data; add --yes to confirm")
        try:
            with open(src, encoding="utf-8") as f, transaction.atomic():
                c = restore_backup(DjangoBackend(), f, replace=replace)
        except (BackupError, OSError) as e:
            raise CommandError(str(e))
        self.stdout.write(f"restored rows={c['rows']} sequences={c['sequences']}; all users must sign in again")

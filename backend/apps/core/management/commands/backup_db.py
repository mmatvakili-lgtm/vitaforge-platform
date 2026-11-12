"""python manage.py backup_db --out backup.json
Writes the whole store as one checksummed JSON file (owner-only permissions, never overwrites). The file contains HEALTH DATA and password hashes:
encrypt it at rest and keep it off shared storage. NEEDS LOCAL VERIFICATION against a real database."""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Back up the persistent store to a JSON file."

    def add_arguments(self, p):
        p.add_argument("--out", required=True)

    def handle(self, *a, out, **o):
        from apps.core.kv_backend import DjangoBackend
        from persistence.backup import write_backup
        try:
            r = write_backup(DjangoBackend(), out)
        except FileExistsError:
            raise CommandError(f"{out} already exists; choose a new file name")
        self.stdout.write(f"backup written: {r['path']} rows={r['rows']} sequences={r['sequences']} sha256={r['sha256']}")
        self.stdout.write("WARNING: the file is not encrypted and contains health data; encrypt it before storing it elsewhere.")

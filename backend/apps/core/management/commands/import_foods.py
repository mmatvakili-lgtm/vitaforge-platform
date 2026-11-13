"""python manage.py import_foods --file FoodData_Central_foundation_food_json.json --retrieved 2026-11-12 [--dataset usda_fdc_foundation] [--dry-run]
Reads a USDA FoodData Central JSON file (Foundation or SR Legacy) you downloaded, validates every record, and stores the valid ones as
PENDING_REVIEW. Existing records are never overwritten. Nothing becomes visible to users until a human reviewer approves it (allergens unknown,
licence unverified until then). NEEDS LOCAL VERIFICATION."""
import json

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Import USDA FDC foods as pending_review."

    def add_arguments(self, p):
        p.add_argument("--file", required=True)
        p.add_argument("--retrieved", required=True, help="date you downloaded the file, YYYY-MM-DD")
        p.add_argument("--dataset", default="usda_fdc_foundation")
        p.add_argument("--dry-run", action="store_true")

    def handle(self, *a, file, retrieved, dataset, dry_run, **o):
        import re

        from apps.core.kv_backend import DjangoBackend
        from nutrition_engine.fdc_import import import_fdc
        from nutrition_engine.loader import load_foods
        from persistence import PersistentStore
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved):
            raise CommandError("--retrieved must be YYYY-MM-DD")
        if not dataset.startswith("usda"):
            raise CommandError("--dataset must start with 'usda' (this importer only understands USDA FDC)")
        try:
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise CommandError(f"cannot read {file}: {e}")
        rep = import_fdc(data, retrieved, dataset)
        self.stdout.write(f"parsed: accepted={len(rep.accepted)} rejected={len(rep.rejected)} duplicates={len(rep.duplicates)} "
                          f"nutrient_mismatches={rep.nutrient_mismatches} energy_warnings={len(rep.energy_warnings)}")
        if dry_run:
            self.stdout.write("dry run: nothing stored"); return
        store = PersistentStore(DjangoBackend())
        with store.transaction():
            r = load_foods(store.foods, rep.accepted)
        self.stdout.write(self.style.SUCCESS(f"stored: added={r['added']} skipped={r['skipped_existing_or_not_pending']}; all pending_review"))

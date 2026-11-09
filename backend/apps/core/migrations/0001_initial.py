# Hand-written to match apps/core/models.py for Django 6.0. NEEDS LOCAL VERIFICATION:
#   python manage.py makemigrations --check --dry-run     (must report "No changes detected")
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="KVRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("coll", models.CharField(max_length=40)),
                ("k", models.CharField(max_length=300)),
                ("owner", models.CharField(blank=True, max_length=60, null=True)),
                ("data", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="IdSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=40, unique=True)),
                ("n", models.BigIntegerField(default=0)),
            ],
        ),
        migrations.AddConstraint(model_name="kvrecord", constraint=models.UniqueConstraint(fields=("coll", "k"), name="kv_unique_coll_key")),
        migrations.AddIndex(model_name="kvrecord", index=models.Index(fields=["coll", "owner"], name="kv_coll_owner_idx")),
    ]

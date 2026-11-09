"""Django-backed tests. Skipped when Django is not installed. NEVER touches your real database: uses VITAFORGE_TEST_DATABASE_URL
(default: a temporary SQLite file). Point it at an empty PostgreSQL database to run the same tests on PostgreSQL."""
import os
import tempfile

import pytest

pytest.importorskip("django")
pytest.importorskip("dj_database_url")

_tmp = tempfile.mkdtemp(prefix="vf-django-")
os.environ["DATABASE_URL"] = os.environ.get("VITAFORGE_TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.sqlite3"
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production-0123456789")
os.environ.setdefault("DJANGO_DEBUG", "true")
os.environ.setdefault("ALLOWED_HOSTS", "localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()


@pytest.fixture(scope="session", autouse=True)
def _migrated():
    from django.core.management import call_command
    call_command("migrate", verbosity=0, interactive=False)


@pytest.fixture(autouse=True)
def _clean(_migrated):
    from apps.core.models import IdSequence, KVRecord
    KVRecord.objects.all().delete()
    IdSequence.objects.all().delete()
    yield

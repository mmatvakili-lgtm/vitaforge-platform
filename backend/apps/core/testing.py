"""Test helper: run the WHOLE existing suite against the Django ORM store.
    set VITAFORGE_TEST_STORE=django
    set VITAFORGE_TEST_DATABASE_URL=postgres://vitaforge:vitaforge@localhost:5432/vitaforge_test     (EMPTY test database; tables are wiped per test)
    python -m pytest -q
Without VITAFORGE_TEST_DATABASE_URL a temporary SQLite file is used. The real DATABASE_URL is never used here. NOT RUN in the cloud environment."""
import os
import tempfile

_ready = False


def _setup():
    global _ready
    if _ready:
        return
    os.environ["DATABASE_URL"] = os.environ.get("VITAFORGE_TEST_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp(prefix='vf-django-')}/test.sqlite3"
    os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production-0123456789")
    os.environ.setdefault("DJANGO_DEBUG", "true")
    os.environ.setdefault("ALLOWED_HOSTS", "localhost")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.core.management import call_command
    call_command("migrate", verbosity=0, interactive=False)
    from .models import IdSequence, KVRecord
    KVRecord.objects.all().delete()                      # once per test session: the test database only
    IdSequence.objects.all().delete()
    _ready = True


def fresh_django_store():
    """A store in its own namespace of the test database (isolated like a new InMemoryStore, even when several coexist)."""
    _setup()
    import uuid
    from persistence import PersistentStore
    from .kv_backend import DjangoBackend
    return PersistentStore(DjangoBackend(namespace=uuid.uuid4().hex[:12]))

"""The shared store conformance suite, executed on the Django ORM backend (NOT RUN in the cloud environment; run locally)."""
import pytest

from apps.core.kv_backend import DjangoBackend
from persistence import PersistentStore
from persistence.tests.conformance import *          # noqa: F401,F403


@pytest.fixture
def new_store():
    return lambda: PersistentStore(DjangoBackend())


def test_owner_column_is_set_for_user_isolation_queries():
    from apps.core.models import KVRecord
    s = PersistentStore(DjangoBackend())
    with s.transaction():
        s.users["u1"] = {"id": "u1"}
        s.sessions["h"] = {"user": "u1", "id": "s"}
        s.plans["u2"] = [{"v": 1}]
    got = {(r.coll, r.k): r.owner for r in KVRecord.objects.all()}
    assert got[("users", '"u1"')] == "u1" and got[("sessions", '"h"')] == "u1" and got[("plans", '"u2"')] == "u2"


def test_check_constraints_and_migration_are_in_sync():
    from django.core.management import call_command
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)       # fails if models.py and 0001_initial.py disagree

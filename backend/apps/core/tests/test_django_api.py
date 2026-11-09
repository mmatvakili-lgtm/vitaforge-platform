"""Contract Harness on the Django stack: spec-driven application on PersistentStore(DjangoBackend); every exchange is checked against OpenAPI.
NOT RUN in the cloud environment; run locally. (For the full suite on Django: see apps/core/testing.py.)"""
from apps.core.kv_backend import DjangoBackend
from contract.harness import Harness
from contract.scenarios import happy_path
from contract.spec import contract
from devserver.bootstrap import build_app
from persistence import PersistentStore

C = contract()


def _h(**kw):
    return Harness(store=PersistentStore(DjangoBackend()), **kw)


def test_every_operation_conforms_to_openapi_on_django_store():
    h = _h()
    happy_path(h)
    assert h.problems == [], h.problems[:5]
    ok = {e.op.id for e in h.log if e.op and e.status == e.op.success_status}
    assert {o.id for o in C.ops} - ok == {"API-SUB-003", "API-ADM-007"}


def test_session_and_data_survive_a_new_store_instance():
    h = _h()
    t = h.login("dj@ex.com")
    assert _h().call("GET", "/profile", token=t).status == 200


def test_production_posture_has_no_content():
    app = build_app(PersistentStore(DjangoBackend()), dev_content=False)
    with app.store.transaction():
        assert len(app.store.catalog) == 0

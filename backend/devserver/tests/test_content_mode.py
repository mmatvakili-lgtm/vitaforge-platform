"""Public ai_curated demo mode: unreviewed content may run under VITAFORGE_ENV=production only with the explicit mode + acknowledgement."""
import pytest

from devserver.bootstrap import build_app
from exercise_catalog.bridge import ProductionCatalogError
from app_services.store import InMemoryStore


def _prod(monkeypatch, mode=None, ack=None):
    monkeypatch.setenv("VITAFORGE_ENV", "production")
    for k, v in (("VITAFORGE_CONTENT_MODE", mode), ("VITAFORGE_ACK_AI_CURATED_CONTENT", ack)):
        monkeypatch.delenv(k, raising=False) if v is None else monkeypatch.setenv(k, v)


@pytest.mark.parametrize("mode,ack", [(None, None), ("ai_curated_demo", None), (None, "yes"), ("ai_curated_demo", "no")])
def test_production_without_full_opt_in_still_refuses_unreviewed_content(monkeypatch, mode, ack):
    _prod(monkeypatch, mode, ack)
    with pytest.raises(ProductionCatalogError):
        build_app(InMemoryStore(), dev_content=True, dev_mode=False, content_mode="ai_curated_demo")


def test_demo_mode_is_reported_by_ready_and_labels_plans(monkeypatch):
    _prod(monkeypatch, "ai_curated_demo", "yes")
    app = build_app(InMemoryStore(), dev_content=True, dev_mode=False, content_mode="ai_curated_demo")
    assert app.content_mode == "ai_curated_demo" and app.rule_set.status == "ai-curated-demo"
    assert app.op_api_sys_002({}) == {"message": "ok", "content_mode": "ai_curated_demo"}


def test_default_app_reports_reviewed():
    app = build_app(InMemoryStore())
    assert app.op_api_sys_002({})["content_mode"] == "reviewed"

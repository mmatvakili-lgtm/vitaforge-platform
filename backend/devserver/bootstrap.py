"""Builds the HTTP application for any store. Used by the dev server (in-memory) and by Django (`config.wsgi`, PersistentStore)."""
from __future__ import annotations

from exercise_catalog import load_starter, relations, to_catalog_entry
from safety_core.models import RuleSet

from .app import SCREENING, App


def build_app(store, dev_content: bool = False, dev_mode: bool = False, mail=None, telegram=None) -> App:
    """`dev_content=True` loads the EXPERIMENTAL sample catalogue and lets the Safety Core accept unreviewed content (LOCAL DEMO ONLY).
    Default (False) is the production posture: no content is published, so plan generation is refused by the Safety Core (SAF-R013)."""
    rows = load_starter()
    if dev_content:
        tx = getattr(store, "transaction", None)
        import contextlib
        with (tx() if tx else contextlib.nullcontext()):
            if not store.catalog:                                  # never overwrite state already in the database
                store.catalog = {r.id: to_catalog_entry(r, dev_experimental=True) for r in rows}
                store.relations = relations(rows)
    rs = RuleSet(version=0, status="dev-demo" if dev_content else "production", screening_questions=SCREENING, allow_unreviewed_content=dev_content)
    app = App(store, rs, dev_mode=dev_mode, mail=mail, telegram=telegram)
    app.layer.kb.records = rows
    app.records = {r.id: r for r in rows}
    return app

"""Builds the HTTP application for any store. Used by the dev server (in-memory) and by Django (`config.wsgi`, PersistentStore)."""
from __future__ import annotations

import functools

from exercise_catalog import load_starter, relations, to_catalog_entry
from safety_core.models import RuleSet

from .app import SCREENING, App


@functools.lru_cache(maxsize=1)
def _starter() -> tuple:
    """The starter bank is static: parse it once per process, not once per request (Django builds an App for every request)."""
    return tuple(load_starter())


def build_app(store, dev_content: bool = False, dev_mode: bool = False, mail=None, telegram=None, content_mode: str = "reviewed", advisory: bool = False) -> App:
    """`dev_content=True` loads the EXPERIMENTAL sample catalogue and lets the Safety Core accept unreviewed content (LOCAL DEMO ONLY).
    Default (False) is the production posture: no content is published, so plan generation is refused by the Safety Core (SAF-R013)."""
    rows = list(_starter())
    if dev_content:
        tx = getattr(store, "transaction", None)
        import contextlib
        with (tx() if tx else contextlib.nullcontext()):
            # Seed once and never overwrite state already in the database. Two point lookups (first/last bank row) replace the former
            # `not store.catalog` which scanned and decoded every catalogue row on EVERY request; rows added by later bank batches are
            # appended without touching existing ones.
            if rows and (rows[0].id not in store.catalog or rows[-1].id not in store.catalog):
                have = set(store.catalog) if len(store.catalog) else set()
                fresh = {r.id: to_catalog_entry(r, dev_experimental=True) for r in rows if r.id not in have}
                for k, v in fresh.items():
                    store.catalog[k] = v
                if fresh:
                    store.relations = relations(rows)
    rs = RuleSet(version=0, status=("ai-curated-demo" if content_mode == "ai_curated_demo" else "dev-demo") if dev_content else "production", screening_questions=SCREENING, allow_unreviewed_content=dev_content, advisory_mode=bool(advisory and dev_content))
    app = App(store, rs, dev_mode=dev_mode, mail=mail, telegram=telegram, content_mode=content_mode if dev_content else "reviewed")
    app.layer.kb.records = rows
    app.records = {r.id: r for r in rows}
    return app

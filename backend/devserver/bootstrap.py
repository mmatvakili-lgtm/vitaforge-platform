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


_SEED_LOCK = __import__("threading").Lock()   # Django serves requests on threads: only one may seed an empty database, the others wait and then find it seeded


def _seed_demo(store, rows) -> None:
    """Seed the demo catalogue and the demo nutrition content once, never overwriting existing state. The common case (already seeded) is two
    cheap point lookups per collection with NO write transaction; only a fresh database takes the lock and a transaction, so concurrent first
    requests queue instead of colliding on the database write lock."""
    from nutrition_engine.demo_content import demo_content
    dfoods, drecipes = demo_content()
    fk, rk = list(dfoods), [r.id for r in drecipes]
    foods, recipes = store.__dict__.setdefault("foods", {}), store.__dict__.setdefault("recipes", {})

    def missing() -> bool:
        return bool((rows and (rows[0].id not in store.catalog or rows[-1].id not in store.catalog))
                    or fk[0] not in foods or fk[-1] not in foods or rk[0] not in recipes or rk[-1] not in recipes)

    if not missing():
        return
    import contextlib
    with _SEED_LOCK:
        tx = getattr(store, "transaction", None)
        with (tx() if tx else contextlib.nullcontext()):
            if not missing():                       # another thread seeded while we waited
                return
            have = set(store.catalog) if len(store.catalog) else set()
            fresh = {r.id: to_catalog_entry(r, dev_experimental=True) for r in rows if r.id not in have}
            for k, v in fresh.items():
                store.catalog[k] = v
            if fresh:
                store.relations = relations(rows)
            for k, v in dfoods.items():
                if k not in foods:
                    foods[k] = v
            for r in drecipes:
                if r.id not in recipes:
                    recipes[r.id] = r


def build_app(store, dev_content: bool = False, dev_mode: bool = False, mail=None, telegram=None, content_mode: str = "reviewed", advisory: bool = False) -> App:
    """`dev_content=True` loads the EXPERIMENTAL sample catalogue and lets the Safety Core accept unreviewed content (LOCAL DEMO ONLY).
    Default (False) is the production posture: no content is published, so plan generation is refused by the Safety Core (SAF-R013)."""
    rows = list(_starter())
    if dev_content:
        _seed_demo(store, rows)
    rs = RuleSet(version=0, status=("ai-curated-demo" if content_mode == "ai_curated_demo" else "dev-demo") if dev_content else "production", screening_questions=SCREENING, allow_unreviewed_content=dev_content, advisory_mode=bool(advisory and dev_content))
    app = App(store, rs, dev_mode=dev_mode, mail=mail, telegram=telegram, content_mode=content_mode if dev_content else "reviewed")
    app.layer.kb.records = rows
    app.records = {r.id: r for r in rows}
    return app

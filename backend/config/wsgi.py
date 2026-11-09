"""WSGI entry. /api/v1/* (except Django-level health) is served by the spec-driven application on a PersistentStore (ADR-0009/0013/0014);
everything else (health, future Django views) by Django. A fresh store + application per request keeps all caches request-local (thread safe).
NEEDS LOCAL VERIFICATION: written without a Django runtime."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
_django = get_wsgi_application()


def _api_app():
    from django.conf import settings

    from apps.core.kv_backend import DjangoBackend
    from devserver.bootstrap import build_app
    from persistence import PersistentStore

    cfg = settings.CFG
    return build_app(PersistentStore(DjangoBackend()), dev_content=cfg["dev_content"], dev_mode=cfg["debug"])


def application(environ, start_response):
    from .routing import goes_to_api
    dev = os.environ.get("VITAFORGE_DEV_CONTENT", "").lower() in ("1", "true", "yes")
    if goes_to_api(environ.get("PATH_INFO", ""), dev):
        return _api_app()(environ, start_response)
    return _django(environ, start_response)

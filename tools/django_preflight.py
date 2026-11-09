"""Preflight for Django runtime validation. Prints exactly what can/cannot run; never fakes a result.
Usage (on a machine with network):  pip install -r backend/requirements.txt && python tools/django_preflight.py"""
import importlib, os, shutil, socket, sys
from urllib.parse import urlparse

ok = True
for mod in ("django", "rest_framework", "psycopg", "dj_database_url", "yaml", "jsonschema", "referencing"):
    try:
        importlib.import_module(mod); print(f"PASS import {mod}")
    except Exception as e:  # noqa: BLE001
        ok = False; print(f"FAIL import {mod}: {e}")
url = os.environ.get("DATABASE_URL", "")
if not url.startswith("postgres"):
    ok = False; print("FAIL DATABASE_URL not set to a postgres URL")
else:
    u = urlparse(url)
    try:
        socket.create_connection((u.hostname or "localhost", u.port or 5432), timeout=3).close(); print("PASS postgres port reachable")
    except OSError as e:
        ok = False; print(f"FAIL postgres not reachable: {e}")
print("psql:", shutil.which("psql") or "not found")
sys.exit(0 if ok else 1)

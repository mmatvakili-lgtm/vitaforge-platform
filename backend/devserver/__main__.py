"""python -m devserver  -> http://127.0.0.1:8000 (DEV ONLY; demo content, in-memory data)."""
import os
from wsgiref.simple_server import make_server

from safety_core.models import RuleSet

from .app import SCREENING, App
from .demo_catalog import demo_catalog
from app_services.store import InMemoryStore

store = InMemoryStore()
store.catalog = demo_catalog()
rs = RuleSet(version=0, status="dev-demo", screening_questions=SCREENING, allow_unreviewed_content=True)
app = App(store, rs, dev_mode=True)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"DEV server on :{port} (demo content, NOT for real users)")
    make_server("127.0.0.1", port, app).serve_forever()

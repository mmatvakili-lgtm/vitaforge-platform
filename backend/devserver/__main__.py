"""python -m devserver  -> http://127.0.0.1:8000 (DEV ONLY; demo content, in-memory data)."""
import os
from wsgiref.simple_server import make_server

from app_services.store import InMemoryStore

from mailer.runtime import capture_runtime

from .bootstrap import build_app

store = InMemoryStore()
app = build_app(store, dev_content=True, dev_mode=True, mail=capture_runtime(store, os.environ.get("DJANGO_SECRET_KEY", "devserver-only-secret-0123456789abcdef")))
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"DEV server on :{port} (demo content, NOT for real users)")
    make_server("127.0.0.1", port, app).serve_forever()

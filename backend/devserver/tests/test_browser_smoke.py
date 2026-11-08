"""Real-browser smoke test of the dev page (skipped, not faked, when Playwright/Chromium is unavailable)."""
import threading
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

pw = pytest.importorskip("playwright.sync_api")
from contract.harness import Harness  # noqa: E402


class Quiet(WSGIRequestHandler):
    def log_message(self, *a):
        pass


def test_register_login_onboard_and_get_plan_in_chromium():
    h = Harness()
    srv = make_server("127.0.0.1", 0, h.app, handler_class=Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with pw.sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"chromium not available: {type(e).__name__}")
            pg = b.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{srv.server_port}/")
            pg.click("#reg"); pg.get_by_text("وارد شدید").wait_for(timeout=8000)
            pg.click("#gen"); pg.locator("#out h3").first.wait_for(timeout=8000)
            assert pg.locator("#out li").count() >= 3 and errs == []
            ck = {c["name"]: c for c in pg.context.cookies()}
            assert ck["sessionid"]["httpOnly"] and not ck["csrftoken"]["httpOnly"]
            b.close()
    finally:
        srv.shutdown()

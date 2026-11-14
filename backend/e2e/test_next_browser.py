"""REAL BROWSER journey through the actual Next.js app (`next dev`, i.e. React StrictMode ON) against the dev API server.
Mocked: Telegram (the dev-only simulate route plays the bot; the single-use token is real). Real: Chromium, Next, React, cookies, proxy, API.
Skipped (not faked) when node_modules, Playwright or Chromium are missing. Catches UI-only bugs the API tests cannot, e.g. a button stuck on 'sending'."""
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "frontend" / "node_modules" / "next").exists() or shutil.which("node") is None, reason="frontend dependencies not installed")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait(url, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=3).read()
            return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise AssertionError("not reachable: " + url)


def test_register_telegram_verify_and_land_on_onboarding_in_real_browser():
    api_port, web_port = free_port(), free_port()
    api = subprocess.Popen([sys.executable, "-m", "devserver"], cwd=ROOT / "backend", env={**os.environ, "PORT": str(api_port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    web = subprocess.Popen(["npx", "next", "dev", "-p", str(web_port)], cwd=ROOT / "frontend", env={**os.environ, "BACKEND_URL": f"http://127.0.0.1:{api_port}", "NEXT_TELEMETRY_DISABLED": "1"},
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait(f"http://127.0.0.1:{api_port}/api/v1/health/live", 30)
        wait(f"http://127.0.0.1:{web_port}/fa/login", 180)
        with pw.sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"chromium not available: {type(e).__name__}")
            pg = b.new_page()
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.set_default_timeout(60000)
            pg.goto(f"http://127.0.0.1:{web_port}/fa/register")
            pg.fill("#email", "browser@ex.com")
            pg.fill("#password", "Str0ng-Passw0rd")
            pg.fill("#dob", "1995-04-12")
            pg.click("button[type=submit]")
            try:
                pg.get_by_role("button", name="تأیید با تلگرام").wait_for(timeout=30000)
            except Exception:  # noqa: BLE001
                raise AssertionError("telegram button not shown; page text: " + pg.inner_text("body")[:800] + " | js errors: " + repr(errors))
            pg.get_by_role("button", name="تأیید با تلگرام").click()
            link = pg.locator("a[href^='https://t.me/']")
            link.wait_for()                                                  # a stuck 'sending…' button would time out here
            href = link.get_attribute("href")
            token = re.search(r"start=([A-Za-z0-9_-]{20,64})$", href).group(1)
            r = urllib.request.Request(f"http://127.0.0.1:{api_port}/api/v1/dev/telegram/simulate-start", data=('{"telegram_id": 880001, "token": "%s"}' % token).encode(),
                                       headers={"Content-Type": "application/json"}, method="POST")
            assert urllib.request.urlopen(r, timeout=10).status == 200       # = the user pressed Start in the bot
            pg.wait_for_url(re.compile(r"/fa/onboarding"), timeout=60000)    # the page detects verification by itself and signs in
            assert errors == []
            b.close()
    finally:
        for proc in (web, api):
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                proc.kill()

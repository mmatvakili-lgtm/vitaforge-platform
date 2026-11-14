"""REAL BROWSER journey through the actual Next.js production build (`next start`) against the dev API server.
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


@pytest.fixture(scope="module")
def stack():
    """One API server + one production Next build shared by every browser test in this module."""
    api_port, web_port = free_port(), free_port()
    api = subprocess.Popen([sys.executable, "-m", "devserver"], cwd=ROOT / "backend", env={**os.environ, "PORT": str(api_port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    env = {**os.environ, "BACKEND_URL": f"http://127.0.0.1:{api_port}", "NEXT_TELEMETRY_DISABLED": "1"}
    # PRODUCTION build (`next start`): deterministic hydration. (`next dev` on CI never hydrated within 90 s; React StrictMode's double mount is covered by a unit regression test.)
    build = subprocess.run(["npx", "next", "build"], cwd=ROOT / "frontend", env=env, capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout[-1500:] + build.stderr[-1500:]
    web = subprocess.Popen(["npx", "next", "start", "-p", str(web_port)], cwd=ROOT / "frontend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait(f"http://127.0.0.1:{api_port}/api/v1/health/live", 30)
        wait(f"http://127.0.0.1:{web_port}/fa/login", 60)
        yield api_port, web_port
    finally:
        for proc in (web, api):
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                proc.kill()


def _browser(p):
    try:
        return p.chromium.launch()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"chromium not available: {type(e).__name__}")


def _hydrated(pg):
    pg.wait_for_function("() => { const f = document.querySelector('form'); return !!f && Object.keys(f).some(k => k.startsWith('__reactProps')); }", timeout=90000)


@pytest.mark.parametrize("mode", ["rate_limited_429", "unavailable_503", "offline"])
def test_login_error_states_are_shown_and_the_form_recovers(stack, mode):
    """UI error states (API failures are simulated at the browser network layer = mocked, the page/JS is real): an alert is shown, the
    submit button is re-enabled (never stuck on 'sending'), and the next attempt works once the API answers again."""
    _, web_port = stack
    with pw.sync_playwright() as p:
        b = _browser(p)
        pg = b.new_page()
        pg.set_default_timeout(30000)
        failing = {"on": True}

        def handler(route):
            if not failing["on"]:
                return route.continue_()
            if mode == "offline":
                return route.abort("internetdisconnected")
            code = 429 if mode == "rate_limited_429" else 503
            route.fulfill(status=code, content_type="application/json", headers={"Retry-After": "5"},
                          body='{"error":{"code":"%s","message":"x","request_id":"req-e2e"}}' % ("rate_limited" if code == 429 else "service_unavailable"))

        pg.route("**/api/v1/auth/login", handler)
        pg.goto(f"http://127.0.0.1:{web_port}/fa/login")
        _hydrated(pg)
        pg.fill("#identifier", "nobody@ex.com")
        pg.fill("#password", "Str0ng-Passw0rd")
        pg.click("button[type=submit]")
        pg.locator(".alert[role=alert]").first.wait_for()
        assert pg.locator("button[type=submit]").is_enabled()           # not stuck on 'sending'
        assert pg.locator(".alert[role=alert]").first.inner_text().strip()    # a visible, non-empty message
        failing["on"] = False                                           # the API is back: the same form must work again
        pg.click("button[type=submit]")
        # the real API now answers 401 for the unknown user: wait until the request finished (button idle again) and an alert is shown
        pg.wait_for_function("() => { const b = document.querySelector('button[type=submit]'); return b && !b.disabled && document.querySelector('.alert[role=alert]'); }")
        assert pg.locator("button[type=submit]").is_enabled()
        b.close()


def test_register_telegram_verify_and_land_on_onboarding_in_real_browser(stack):
    api_port, web_port = stack
    if True:
        with pw.sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:  # noqa: BLE001
                pytest.skip(f"chromium not available: {type(e).__name__}")
            pg = b.new_page()
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append("console:" + m.type + ":" + m.text[:300]) if m.type in ("error", "warning") else None)
            pg.on("requestfailed", lambda r: errors.append("reqfail:" + r.url[:120]))
            pg.on("response", lambda r: errors.append(f"http{r.status}:{r.url[:100]}") if r.status >= 400 else None)
            pg.set_default_timeout(60000)
            pg.goto(f"http://127.0.0.1:{web_port}/fa/register")
            # A click before hydration would submit the form natively (GET /fa/register?). Wait for React to attach.
            try:
                pg.wait_for_function("() => { const f = document.querySelector('form'); return !!f && Object.keys(f).some(k => k.startsWith('__reactProps')); }", timeout=90000)
            except Exception:  # noqa: BLE001
                raise AssertionError("page never hydrated: " + pg.url + " | form keys: " + repr(pg.evaluate("() => { const f = document.querySelector('form'); return f ? Object.keys(f) : null; }")) + " | scripts: " + repr(pg.evaluate("() => [...document.scripts].map(s => s.src).slice(0, 8)")) + " | errors: " + repr(errors)[:2500])
            pg.fill("#email", "browser@ex.com")
            pg.fill("#password", "Str0ng-Passw0rd")
            pg.fill("#dob", "1995-04-12")
            pg.click("button[type=submit]")
            try:
                pg.get_by_role("button", name="تأیید با تلگرام").wait_for(timeout=30000)
            except Exception:  # noqa: BLE001
                raise AssertionError("telegram button not shown; page text: " + pg.url + " | " + pg.inner_text("body")[:400] + " | html: " + pg.content()[-1500:] + " | js errors: " + repr(errors)[:1500])
            pg.get_by_role("button", name="تأیید با تلگرام").click()
            link = pg.locator("a[href^='https://t.me/']")
            link.wait_for()                                                  # a stuck 'sending…' button would time out here
            href = link.get_attribute("href")
            token = re.search(r"start=([A-Za-z0-9_-]{20,64})$", href).group(1)
            r = urllib.request.Request(f"http://127.0.0.1:{api_port}/api/v1/dev/telegram/simulate-start", data=('{"telegram_id": 880001, "token": "%s"}' % token).encode(),
                                       headers={"Content-Type": "application/json"}, method="POST")
            assert urllib.request.urlopen(r, timeout=10).status == 200       # = the user pressed Start in the bot
            pg.wait_for_url(re.compile(r"/fa/onboarding"), timeout=60000)    # the page detects verification by itself and signs in
            assert not [e for e in errors if "Content Security Policy" in e or "Refused to" in e], errors      # the CSP must not break the app
            assert not [e for e in errors if not e.startswith(("console:", "reqfail:", "http"))], errors     # no uncaught JS errors
            b.close()

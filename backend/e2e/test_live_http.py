"""REAL-HTTP integration: the frontend's own typed client + page logic (frontend/scripts/e2e-flow.ts, run by Node) against the dev server
started as a separate process. Mocked: Telegram bot and e-mail (capture adapters). Real: HTTP, cookies, CSRF, contract client, all business logic.
Skipped (not faked) when node is unavailable."""
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_frontend_client_full_journey_against_live_http_server():
    port = free_port()
    srv = subprocess.Popen([sys.executable, "-m", "devserver"], cwd=ROOT / "backend", env={**os.environ, "PORT": str(port)}, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        url = f"http://127.0.0.1:{port}/api/v1/health/live"
        for _ in range(60):
            try:
                urllib.request.urlopen(url, timeout=1).read()
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.25)
        else:
            pytest.fail("dev server did not start: " + srv.stderr.read().decode()[-500:])
        r = subprocess.run([NODE, "--experimental-strip-types", "scripts/e2e-flow.ts", f"http://127.0.0.1:{port}/api/v1"], cwd=ROOT / "frontend",
                           capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stdout[-2500:] + r.stderr[-1500:]
        assert "telegram verification (mocked bot)" in r.stdout and "logout" in r.stdout
    finally:
        srv.terminate()
        srv.wait(timeout=10)

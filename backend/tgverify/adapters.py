from __future__ import annotations

import json
import urllib.request
from typing import List

from .ports import TelegramSender


class CaptureSender(TelegramSender):
    """Development/test adapter: records what the bot WOULD send. Nothing leaves the machine."""
    provider = "capture"

    def __init__(self):
        self.sent: List[dict] = []

    def send_message(self, chat_id: int, text: str) -> bool:
        self.sent.append({"chat_id": chat_id, "text": text})
        return True


class BotApiSender(TelegramSender):
    """Real Telegram Bot API (https://api.telegram.org). The token is only ever used to build the request URL and is never logged or raised."""
    provider = "live"
    delivers_real_messages = True

    def __init__(self, token: str, timeout: float = 5.0):
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._timeout = timeout

    def send_message(self, chat_id: int, text: str) -> bool:
        body = json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(self._url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as r:     # noqa: S310 (fixed https URL)
                return 200 <= r.status < 300
        except Exception:  # noqa: BLE001  network/HTTP errors must not leak the URL (it contains the token)
            return False

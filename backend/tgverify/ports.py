from __future__ import annotations


class TelegramSender:
    provider = "abstract"
    delivers_real_messages = False

    def send_message(self, chat_id: int, text: str) -> bool:
        """Best effort; returns False on failure and never raises. `text` must never contain health data."""
        raise NotImplementedError


class DisabledSender(TelegramSender):
    provider = "disabled"

    def send_message(self, chat_id: int, text: str) -> bool:
        return False

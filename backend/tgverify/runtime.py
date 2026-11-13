from __future__ import annotations

import dataclasses

from .adapters import BotApiSender, CaptureSender
from .ports import DisabledSender, TelegramSender


@dataclasses.dataclass(frozen=True)
class TelegramRuntime:
    sender: TelegramSender
    username: str
    webhook_secret: str

    @property
    def available(self) -> bool:
        return self.sender.provider != "disabled" and bool(self.username)


def build_runtime(cfg: dict) -> TelegramRuntime:
    if cfg["provider"] == "live":
        return TelegramRuntime(BotApiSender(cfg["token"]), cfg["username"], cfg["webhook_secret"])
    if cfg["provider"] == "capture":
        return TelegramRuntime(CaptureSender(), cfg["username"], cfg["webhook_secret"])
    return TelegramRuntime(DisabledSender(), "", cfg.get("webhook_secret", ""))


def capture_runtime(username: str = "vitaforge_dev_bot", secret: str = "dev-webhook-secret-0123456789abcdef") -> TelegramRuntime:
    """Explicit development/test runtime (never delivers anything)."""
    return TelegramRuntime(CaptureSender(), username, secret)

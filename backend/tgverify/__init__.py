"""Telegram account verification (primary channel). Stdlib only; no paid services. See docs/TELEGRAM_VERIFICATION.md."""
from .config import TelegramConfigError, load_telegram_config
from .runtime import TelegramRuntime, build_runtime, capture_runtime
from .service import TelegramVerification

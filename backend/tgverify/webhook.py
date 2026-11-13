"""Parsing of Telegram `Update` objects. Strict: anything unexpected is ignored, never raised."""
from __future__ import annotations

import re
from typing import Optional, Tuple

START = re.compile(r"^/start(?:@[A-Za-z0-9_]{5,32})?(?:\s+([A-Za-z0-9_-]{20,64}))?$")

SUCCESS_TEXT = "✅ Your VitaForge account is verified. Return to the app and sign in.\n✅ حساب VitaForge شما تأیید شد. به برنامه برگردید و وارد شوید."
FAILURE_TEXT = "❌ This link is invalid or has expired. Request a new one in VitaForge.\n❌ این لینک نامعتبر یا منقضی است. در VitaForge لینک تازه بگیرید."
HELP_TEXT = "Open the verification link from VitaForge to continue.\nبرای ادامه، لینک تأیید را از داخل VitaForge باز کنید."


def parse_start(update) -> Optional[Tuple[int, Optional[str]]]:
    """-> (numeric telegram user id, token or None) for a private-chat /start message; None for everything else.
    Identity is the NUMERIC id only (never the username); group chats, bots, edited messages and forwarded content are ignored."""
    if not isinstance(update, dict) or not isinstance(update.get("message"), dict):
        return None
    msg = update["message"]
    frm, chat, text = msg.get("from"), msg.get("chat"), msg.get("text")
    if not (isinstance(frm, dict) and isinstance(chat, dict) and isinstance(text, str)) or len(text) > 128:
        return None
    uid = frm.get("id")
    if isinstance(uid, bool) or not isinstance(uid, int) or uid <= 0 or frm.get("is_bot") is True:
        return None
    if chat.get("type") != "private" or chat.get("id") != uid:
        return None
    if "forward_origin" in msg or "forward_from" in msg or "via_bot" in msg:
        return None
    m = START.match(text.strip())
    return (uid, m.group(1)) if m else None

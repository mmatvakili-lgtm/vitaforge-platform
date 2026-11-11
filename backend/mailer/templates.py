"""EN/FA bodies. Codes and links appear only in the rendered message, never in logs."""
from __future__ import annotations

from html import escape

_T = {
    "fa": {
        "verification": ("کد تأیید حساب VitaForge",
                         "کد تأیید شما: {code}\nاین کد ۳۰ دقیقه معتبر است. اگر شما ثبت‌نام نکرده‌اید، این پیام را نادیده بگیرید."),
        "password_reset": ("بازیابی رمز عبور VitaForge",
                           "برای تعیین رمز جدید این پیوند را باز کنید:\n{link}\nاین پیوند ۳۰ دقیقه معتبر و فقط یک‌بار قابل استفاده است. اگر شما درخواست نداده‌اید، این پیام را نادیده بگیرید."),
        "dir": "rtl",
    },
    "en": {
        "verification": ("Your VitaForge verification code",
                         "Your verification code: {code}\nIt is valid for 30 minutes. If you did not sign up, ignore this message."),
        "password_reset": ("Reset your VitaForge password",
                           "Open this link to choose a new password:\n{link}\nIt is valid for 30 minutes and can be used once. If you did not ask for this, ignore this message."),
        "dir": "ltr",
    },
}


def _render(kind: str, locale: str, **kw):
    t = _T.get(locale) or _T["en"]
    subject, body = t[kind]
    text = body.format(**kw)
    html = f'<div dir="{t["dir"]}">' + "<br>".join(escape(line) for line in text.split("\n")) + "</div>"
    return subject, text, html


def verification(code: str, locale: str):
    return _render("verification", locale, code=code)


def password_reset(link: str, locale: str):
    return _render("password_reset", locale, link=link)

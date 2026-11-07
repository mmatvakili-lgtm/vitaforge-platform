# ADR-0001 — Modular Monolith

| فیلد | مقدار |
|---|---|
| Status | Accepted |
| Date | 2026-11-07 |
| Owner | Architect |
| Related Decisions | سند مادر §26؛ DEC-007 |
| Related Documents | DOC-03، DOC-20 |

شروع با یک اپلیکیشن Django با ماژول‌های جدا (accounts، profiles، health، safety، exercises، workout_engine …).
**گزینه‌ها:** Microservices زودهنگام؛ Monolith بدون مرز؛ Modular Monolith.
**انتخاب:** Modular Monolith.
**دلیل:** ریسک اصلی محصول ایمنی و صحت است نه مقیاس؛ پیچیدگی عملیاتی کمتر؛ مرزها امکان جداسازی بعدی را حفظ می‌کنند.
**پیامد:** ارتباط ماژول‌ها فقط از طریق Interface عمومی؛ کنترل وابستگی با import-linter در CI؛ جداسازی سرویس (مثلاً AI Gateway) در آینده با هزینه کم.
**ریسک:** فرسایش مرز ماژول‌ها؛ کاهش: قاعده import-linter و بازبینی معماری.

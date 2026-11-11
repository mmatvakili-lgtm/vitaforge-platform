<div dir="rtl">

# EXECUTION_ROADMAP — نقشه‌ی اجرا

| فیلد | مقدار |
|---|---|
| Document ID | DOC-ROADMAP |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-11 |

اولویت: ایمنی > حریم/امنیت > دقت علمی > محصول > UX. هر فاز با تست متمرکز؛ تست کامل فقط در مرز milestone.

| فاز | محتوا | وضعیت | مسدودکننده |
|---|---|---|---|
| 0 | ممیزی واقعیت مخزن | انجام شد (`PROJECT_STATE.md`) | — |
| 1a | ایمیل: توکن پایدار، outbox، SMTP/capture، resend، rate limit، قالب FA/EN | کد و تست انجام شد؛ ارسال واقعی منتظر SMTP | اعتبار SMTP |
| 1b | مسیر PostgreSQL، backup/restore، export/delete | **بعدی** | — |
| 2 | سیستم طراحی و UX | PLANNED | — |
| 3 | پایگاه حرکات بازبینی‌شده + ابزار بازبینی ادمین | PLANNED | متخصص، لایسنس |
| 4 | موتور تمرین + ثبت تمرین | PLANNED | فاز ۳ |
| 5 | پایگاه و موتور تغذیه + ثبت وعده | PLANNED | داده FDC، بازبینی |
| 6 | ارائه‌دهنده‌ی AI | PLANNED | بازبینی حقوقی/حریم |
| 7 | پیشرفت، اشتراک، پرداخت | PLANNED | OPEN-001/005 |
| 8 | امنیت/کارایی | PLANNED | — |
| 9 | انتشار | PLANNED | همه‌ی Blockedها |

## دسته‌ی بعدی (روش جدید: دسته‌های بزرگ)

Batch B: تغذیه — مرور غذاها، دستور پخت، لاگ وعده/آب، لیست خرید، بودجه؛ پروفایل و progression تمرین. (قبل از آن: تأیید Django/SMTP روی ماشین مالک.)

## milestone قبلی

تأیید روی ماشین مالک (Django + SQLite/PostgreSQL، `mail_status --send-test`) سپس Phase 1b: PostgreSQL، backup/restore، export/delete.

</div>

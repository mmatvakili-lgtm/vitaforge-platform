<div dir="rtl">

# RELEASE_CHECKLIST — وضعیت واقعی MVP

| فیلد | مقدار |
|---|---|
| Document ID | DOC-REL |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-11 |

| مورد | وضعیت | شواهد |
|---|---|---|
| هسته ایمنی، موتور تمرین، AI Gateway، Entitlement، سرویس‌های کاربردی | `Passed` | `cd backend && python3 -m pytest -q` ← ۵۲۸ تست سبز (in-memory و sqlite) |
| تطابق API توسعه با OpenAPI (هر ۵۹ endpoint) | `Passed` | تست `test_every_openapi_endpoint_is_implemented`؛ فقط وجود مسیر، نه تطابق کامل schema |
| API توسعه (WSGI) + UI آزمایشی | `Passed` (فقط توسعه) | تست HTTP + اجرای واقعی `python3 -m devserver` |
| داده حرکات بازبینی‌شده و دارای منبع علمی | `Blocked` | `OPEN-003/007`؛ فقط ۲۵ حرکت `experimental` |
| آداپتور Django + مهاجرت‌ها | `Passed` (CI/مالک؛ در sandbox اجرا نشده) | job `django-store` روی PostgreSQL؛ تأیید ویندوز/SQLite معلق |
| Next.js | `Passed` (گزارش مالک) | install/tsc/۲۹ تست/build روی ویندوز؛ در CI نیست |
| توکن‌ها و outbox پایدار | `Passed` (خودکار، in-memory+sqlite) | `mailer/tests` |
| تحویل واقعی SMTP | `Blocked` | اعتبار SMTP و `mail_status --send-test`؛ `PROJECT_STATE.md` §۴ |
| انتشار محتوا | `Blocked` | ۰ حرکت و ۰ غذای منتشرشده |
| Docker/CI | `Not Run` | فایل‌ها نوشته شده |
| محتوای بالینی (حرکات، قواعد R1xx..R5xx، مسیر B فعال) | `Blocked` | `OPEN-003`، `EXP-001..013` |
| بررسی حقوقی و ارسال داده سلامت به AI | `Blocked` | `OPEN-002`، `OPEN-004` |
| محتوای حمایتی/ریکاوری برای مشکلات جسمی | `Blocked` | `OPEN-008` |
| پرداخت | `Blocked` | `OPEN-001`، `OPEN-005` (`PaymentProvider` غیرفعال) |

انتشار برای کاربر واقعی ممنوع است تا `Blocked`ها بسته شوند.

</div>

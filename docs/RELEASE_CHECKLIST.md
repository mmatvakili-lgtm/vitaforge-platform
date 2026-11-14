<div dir="rtl">

# RELEASE_CHECKLIST — وضعیت واقعی MVP

| فیلد | مقدار |
|---|---|
| Document ID | DOC-REL |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-12 |

| مورد | وضعیت | شواهد |
|---|---|---|
| هسته ایمنی، موتور تمرین، AI Gateway، Entitlement، سرویس‌های کاربردی | `Passed` | `cd backend && python3 -m pytest -q` ← ۵۵۳ تست سبز (in-memory و sqlite)؛ روی ماشین مالک در حالت Django ← ۵۳۷ سبز و ۲ skip |
| تطابق API توسعه با OpenAPI (هر ۸۲ endpoint) | `Passed` | تست `test_every_openapi_endpoint_is_implemented`؛ فقط وجود مسیر، نه تطابق کامل schema |
| API توسعه (WSGI) + UI آزمایشی | `Passed` (فقط توسعه) | تست HTTP + اجرای واقعی `python3 -m devserver` |
| داده حرکات بازبینی‌شده و دارای منبع علمی | `Blocked` | `OPEN-003/007`؛ فقط ۲۵ حرکت `experimental` |
| آداپتور Django + مهاجرت‌ها | `Passed` (CI/مالک؛ در sandbox اجرا نشده) | job `django-store` روی PostgreSQL؛ تأیید ویندوز/SQLite معلق |
| Next.js | `Passed` (اجرای مالک، ۲۰۲۶-۱۱-۱۲) | `npm ci`، `tsc --noEmit` و `next build` (۳۷ صفحه) روی ویندوز بدون خطا؛ ۴۸ تست Node در sandbox؛ در CI نیست |
| توکن‌ها و outbox پایدار | `Passed` (خودکار، in-memory+sqlite) | `mailer/tests` |
| تحویل واقعی SMTP | `Blocked` | اعتبار SMTP و `mail_status --send-test`؛ `PROJECT_STATE.md` §۴ |
| انتشار محتوا | `Blocked` | ۰ حرکت و ۰ غذای منتشرشده |
| Django + SQLite روی ماشین مالک | `Passed` (اجرای مالک) | `migrate` و pytest در حالت Django |
| PostgreSQL واقعی | `Passed` (CI، job `django-postgres`، PostgreSQL ۱۶) | `makemigrations --check` + کل تست‌ها؛ اجرای مالک روی داده‌ی واقعی هنوز لازم است |
| `npm audit` / `pip-audit` | `Passed` (CI، job `security`) | سطح high؛ Next ارتقا به ۱۶.۴.۶ |
| پشتیبان‌گیری/بازیابی روی Postgres | `Not Run` | `backup_db` سپس `restore_db` روی دیتابیس خالی و مقایسه‌ی تعداد ردیف‌ها؛ رمزنگاری فایل پشتیبان با مالک |
| CI + Docker | `Passed` | شش job؛ image های api و web ساخته می‌شوند و کانتینر api بوت می‌شود و `/health/live` پاسخ می‌دهد؛ کل compose هنوز اجرا نشده |
| محتوای بالینی (حرکات، قواعد R1xx..R5xx، مسیر B فعال) | `Blocked` | `OPEN-003`، `EXP-001..013` |
| بررسی حقوقی و ارسال داده سلامت به AI | `Blocked` | `OPEN-002`، `OPEN-004` |
| محتوای حمایتی/ریکاوری برای مشکلات جسمی | `Blocked` | `OPEN-008` |
| پرداخت | `Blocked` | `OPEN-001`، `OPEN-005` (`PaymentProvider` غیرفعال) |

## کارهای مالک (پس از پایان توسعه)

راهنمای کامل و گام‌به‌گام: `docs/OWNER_GUIDE.md`.

1. SMTP: سرویس + اعتبارنامه، `MAIL_PROVIDER=smtp`، `python manage.py mail_status --send-test you@example.com`، دیدن ایمیل در صندوق.
2. PostgreSQL: `DATABASE_URL`، `migrate`، pytest.
3. `npm audit` و بررسی خروجی (بدون `--force` کورکورانه).
4. واردسازی داده‌ی غذا (FDC) و مجوزها؛ بازبینی متخصص تغذیه و تمرین؛ بررسی حقوقی.
5. بررسی دستی UI روی موبایل و RTL (foods، nutrition/log، history، profile).

انتشار برای کاربر واقعی ممنوع است تا `Blocked`ها بسته شوند.

</div>

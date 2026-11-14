<div dir="rtl">

# ACCEPTANCE_CHECKLIST — چک‌لیست پذیرش نهایی (مالک)

| فیلد | مقدار |
|---|---|
| Document ID | DOC-ACC |
| Version | 0.1 |
| Status | Active (پیش‌نویس RC؛ هنوز release candidate اعلام نشده) |
| Updated | 2026-11-14 |

این تنها فهرستی است که مالک در چرخه‌ی پذیرش نهایی دنبال می‌کند. جزئیات هر مورد در `docs/OWNER_GUIDE.md` و `docs/RELEASE_CHECKLIST.md` است. وضعیت‌ها فقط بر پایه‌ی اجرای واقعی نوشته شده‌اند.

## الف) تأییدشده‌ی خودکار (CI روی GitHub، هر push)

| مورد | وضعیت |
|---|---|
| تست‌های backend (حافظه + sqlite) و contract برای ۸۲ endpoint | `Passed` |
| Django + PostgreSQL ۱۶ (`makemigrations --check` + کل تست‌ها) | `Passed` |
| `tsc --noEmit`، تست‌های Node، `next build` (Next 16) | `Passed` |
| e2e روی سرور HTTP واقعی با کلاینت فرانت (ثبت‌نام، تأیید تلگرام، onboarding، تمرین، تغذیه، داشبورد، REFER) | `Passed` (تلگرام/ایمیل mock) |
| e2e در مرورگر واقعی Chromium روی build تولیدی (ثبت‌نام → تلگرام → onboarding) + نبود خطای CSP | `Passed` (تلگرام mock) |
| ساخت image های api/web و بوت کانتینر api با `/health/live` | `Passed` |
| `pip-audit`، `npm audit` (سطح high)، اسکن secret | `Passed` |
| هدرهای امنیتی و CSP (self-only) | `Passed` |

## ب) تأییدشده توسط مالک

| مورد | وضعیت |
|---|---|
| تأیید حساب با بات واقعی تلگرام (long polling) | `Passed` (۲۰۲۶-۱۱-۱۳) |

## ج) کارهای مالک (وابسته به حساب/اعتبار/انسان)

| # | کار | چرا لازم است | راهنما |
|---|---|---|---|
| 1 | چرخاندن توکن بات (`/revoke` در BotFather) و ساخت secret جدید | توکن و secret در اسکرین‌شات دیده شدند | `TELEGRAM_VERIFICATION.md` |
| 2 | دامنه + HTTPS + سرور؛ `.env` production؛ `telegram_set_webhook --url ...` | وبهوک production اجرا نشده است؛ `telegram_poll` فقط برای توسعه است | `TELEGRAM_VERIFICATION.md` §ج |
| 3 | `npm install` و commit کردن `frontend/package-lock.json` (از طریق PR) | فایل lock در مخزن نیست؛ نصب قابل بازتولید نیست | — |
| 4 | واردسازی داده‌ی FDC و بازبینی غذاها (مالک یا متخصص تغذیه) | بدون آن برنامه‌ی غذایی `NEEDS_CONTENT` است | `OWNER_GUIDE.md` گام ۴ |
| 5 | بازبینی متخصص تمرین و ایمنی بالینی؛ انتشار حرکات | تا آن موقع برنامه‌ی تمرین `NEEDS_CONTENT` و محصول «آزمایشی» است (OPEN-003) | گام ۵ و ۸ |
| 6 | بررسی حقوقی: حریم خصوصی، شرایط استفاده، مجوز داده‌ها، متن رضایت‌ها | OPEN-002، OPEN-004؛ ارسال داده‌ی سلامت به AI تا آن موقع خاموش است | گام ۸ |
| 7 | PostgreSQL production، `migrate`، `backup_db` سپس `restore_db` روی دیتابیس خالی، زمان‌بندی پشتیبان | اجرای واقعی روی داده‌ی واقعی تأیید نشده | گام ۳ |
| 8 | بررسی دستی UI روی موبایل و RTL، نصب PWA، دسترس‌پذیری | تست خودکار ظاهر و تجربه را تأیید نمی‌کند | گام ۷ |
| 9 | (اختیاری) SMTP | با بات تلگرام فعال، ایمیل اختیاری است | گام ۲ |
| 10 | اجرای `docker compose` کامل روی ماشین هدف | فقط image ها در CI بوت شده‌اند، compose کامل اجرا نشده | `infra/docker-compose.yml` |

## د) عمداً غیرفعال / خارج از MVP تا تصمیم مالک

- پرداخت و اشتراک (`PaymentProvider` غیرفعال؛ OPEN-001/005؛ PROG-002 به همین دلیل Deferred).
- ارائه‌دهنده‌ی AI و ارسال داده‌ی سلامت به آن (`AI_EXTERNAL_HEALTH_DATA=false`).
- اعلان‌های تلگرام (فقط رضایت ثبت می‌شود؛ ارسالی وجود ندارد).
- ثبت‌نام با تلفن، مراحل ۵–۱۴ onboarding، enum رضایت `privacy`، `stop_criteria_key` (ثبت‌شده در `API_GAPS.md`).

## هـ) محدودیت‌های شناخته‌شده

- تست مرورگر روی build تولیدی اجرا می‌شود؛ رفتار دوباره‌mount در حالت dev فقط با تست واحد محافظت می‌شود.
- ارسال پیام بات داخل تراکنش درخواست است و شکستش تأیید را خنثی نمی‌کند.
- لغو اتصال تلگرام فقط با حذف حساب ممکن است.
- CSP از `'unsafe-inline'` برای اسکریپت‌های bootstrap خود Next استفاده می‌کند (نسخه‌ی nonce-محور هنوز نیست).

</div>

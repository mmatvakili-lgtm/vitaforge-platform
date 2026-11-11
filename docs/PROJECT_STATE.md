<div dir="rtl">

# PROJECT_STATE — وضعیت واقعی VitaForge

| فیلد | مقدار |
|---|---|
| Document ID | DOC-STATE |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-11 |
| مبنا | commit `4086430`، شاخه `main`، درخت تمیز |

واژگان وضعیت: `PLANNED` · `IMPLEMENTED` · `AUTOMATED_TESTED` · `RUNTIME_VERIFIED` · `PRODUCTION_READY`. هیچ قابلیتی `PRODUCTION_READY` نیست.

## ۱. معماری (تأییدشده از کد)

- مونولیت ماژولار: `backend/` (Safety Core، workout_engine، nutrition_engine، exercise_catalog، ai_gateway، app_services، devserver، contract)، `frontend/` (Next.js 15، fa/en)، `docs/`، `tools/`.
- API: برنامه‌ی spec-driven (`devserver/app.py`) که با `config/wsgi.py` زیر Django سرو می‌شود؛ همه‌ی `/api/v1/*` به آن می‌رود (`config/routing.py`). OpenAPI: ۵۹ عملیات.
- نشست: کوکی HttpOnly + CSRF double-submit (ADR-0009).

## ۲. جدول وضعیت قابلیت‌ها

| قابلیت | وضعیت | شواهد / محدودیت |
|---|---|---|
| Safety Core | `AUTOMATED_TESTED` | تست‌های backend (۴۷۲ سبز، حالت in-memory و sqlite) |
| تطابق OpenAPI با مسیرها | `AUTOMATED_TESTED` | Contract Harness هر ۵۹ عملیات را اجرا و پاسخ را با spec می‌سنجد |
| Frontend (مسیرها: home, login, register, verify, onboarding, plan, exercises/[id], nutrition) | `AUTOMATED_TESTED` | ۲۹ تست Node + e2e با devserver؛ همه‌ی لینک‌ها به صفحه‌ی موجود می‌رسند. اجرای install/tsc/build را مالک روی ویندوز گزارش کرده، در این sandbox اجرا نشده |
| ثبت‌نام / ورود / خروج | `AUTOMATED_TESTED` | فقط در devserver و تست |
| **تأیید ایمیل** | `PLANNED` (کد ناقص) | بخش ۴ |
| بازیابی رمز | `PLANNED` (کد ناقص) | همان مشکل: توکن در حافظه |
| پایگاه داده | `IMPLEMENTED` | بخش ۳ |
| موتور تمرین | `AUTOMATED_TESTED` | محتوا فقط `experimental_unreviewed` |
| کاتالوگ حرکات | محتوا بسته | ۳۰ حرکت اولیه، ۰ منتشرشده؛ ۸۷۶ رکورد staging همگی `pending_review` و لایسنس نامعتبر |
| موتور تغذیه | `AUTOMATED_TESTED` | بدون غذای بازبینی‌شده → `NEEDS_CONTENT`؛ واردکننده‌ی FDC اجرا نشده |
| ارائه‌دهنده‌ی AI | `PLANNED` | فقط `StubProvider` |
| پرداخت/اشتراک | `PLANNED` | `PaymentProvider` غیرفعال |
| پشتیبان‌گیری/بازیابی، export/delete حریم خصوصی | `PLANNED` | بررسی نشد؛ گزارش پیاده‌سازی وجود ندارد |

## ۳. پایگاه داده و ماندگاری

- همه‌ی داده در یک KV store (`PersistentStore`) ذخیره می‌شود؛ زیر Django از `apps/core/kv_backend.py` و `DATABASE_URL` (با `dj_database_url`) استفاده می‌کند. هر درخواست App و store تازه می‌سازد.
- SQLite یا PostgreSQL فقط با `DATABASE_URL` تعیین می‌شود. `.env.example`، compose و CI روی PostgreSQL‌اند؛ مالک با SQLite کار می‌کند. ماندگاری بین ری‌استارت روی PostgreSQL در CI آزمون می‌شود (job `django-store`)؛ روی SQLite ویندوز توسط مالک تأیید نشده (`VITAFORGE_TEST_STORE=django`).
- مهاجرت‌ها: CI `makemigrations --check` اجرا می‌کند.

## ۴. ایمیل (کد ≠ تحویل واقعی SMTP)

- هیچ آداپتور ایمیل/SMTP وجود ندارد (جست‌وجوی EMAIL/SMTP در settings خالی است).
- کد تأیید هش‌شده در `store.verification` ذخیره می‌شود (انقضای ۳۰ دقیقه)، اما متن کد فقط در `App.sent_codes` (حافظه) در حالت dev می‌ماند؛ توکن بازیابی در `sent_resets`.
- زیر Django، `config/wsgi.py` با `dev_mode=cfg["debug"]` ساخته می‌شود: با `DEBUG=true` ثبت‌نام فوراً تأیید می‌شود (auto_verify)؛ با `DEBUG=false` کد هرگز به کاربر نمی‌رسد و تأیید ناممکن است.
- نتیجه: «ایمیل نمی‌رسد» ریشه‌ی واقعی دارد (نبود ارسال)، نه خطای SMTP.

## ۵. طبقه‌بندی 404

بررسی کد: لینک‌های frontend همگی به صفحات موجودند؛ مسیرهای `/api/v1/*` همگی توسط OpenAPI پوشش دارند. 404های محتمل:

| منبع | دسته |
|---|---|
| مسیر خارج از `/api/v1/` روی backend (مثل `/`) وقتی `VITAFORGE_DEV_CONTENT=false` | expected 404 |
| `/api/v1/nutrition/{meals,water,summary}` و `/foods`, `/recipes` | missing backend (در `x-deferred`) |
| `/nutrition/estimate`, `/nutrition/meal-plan` (حذف‌شده) | `wrong frontend URL` / قدیمی |
| آدرس بدون `/fa` یا `/en` | middleware ریدایرکت می‌کند؛ ۴۰۴ نیست |
| منابع بدون پروفایل (`/nutrition/*`) | expected 404 (domain) |
| کاربر ناوارد روی endpoint محافظت‌شده | ۴۰۱ است، نه ۴۰۴ |

ورودی مشخص مالک (URL دقیق) برای ۴۰۴های گزارش‌شده در دسترس نبود؛ هر URL جدید با این جدول رده‌بندی می‌شود.

## ۵.۱ مسدودها (نیاز به متخصص/تأیید بیرونی)

محتوای بالینی، بازبینی حقوقی، لایسنس تصاویر و دادگان، پرداخت، ارسال داده سلامت به AI — طبق `RELEASE_CHECKLIST.md` در وضعیت `Blocked`/Pending Review.

## ۶. فهرست مسائل (اولویت‌دار)

| # | شدت | ماژول/فایل | رفتار مشاهده‌شده | رفتار مورد انتظار | ریشه (تأییدشده) | راه‌حل | وابستگی | تست پذیرش |
|---|---|---|---|---|---|---|---|---|
| 1 | Critical | `devserver/app.py` AUTH-001/005، `config/wsgi.py` | کد/توکن هرگز ارسال نمی‌شود | ایمیل واقعی با توکن تک‌مصرف | نبود mail adapter؛ `sent_codes` در حافظه | پورت `MailSender` + outbox پایدار + SMTP؛ ثبت‌نام/بازیابی از آن بگذرد | اعتبار SMTP برای ارسال واقعی | ثبت‌نام → outbox پایدار؛ تست با SMTP محلی؛ ری‌استارت نگه می‌دارد |
| 2 | Critical | کاتالوگ حرکات | ۰ حرکت منتشرشده؛ برنامه‌ها `experimental_unreviewed` | فقط حرکات بازبینی‌شده | نبود بازبینی متخصص/لایسنس | ابزار بازبینی ادمین؛ ماندن Pending Review | متخصص | تست دروازه‌ی انتشار (موجود) + UI بازبینی |
| 3 | High | `.env`/DB | مالک SQLite دارد؛ مسیر PostgreSQL فقط در CI | مسیر PostgreSQL مستند و تأییدشده | — | دستور اجرا و بررسی ری‌استارت | — | تست ماندگاری روی PG |
| 4 | High | حریم خصوصی | export/delete، backup/restore ناموجود | موجود و تست‌شده | پیاده‌سازی نشده | Phase 1 | — | تست export/delete/restore |
| 5 | High | rate limiting | بررسی نشد/ناموجود برای auth | محدودیت نرخ | — | افزودن همراه mail | — | تست ۴۲۹ |
| 6 | Medium | `ai_gateway` | فقط Stub | provider واقعی پشت بازبینی حریم | OPEN-002/004 | Phase 6 | بازبینی حقوقی | — |
| 7 | Medium | نگهداری FDC | واردکننده اجرا نشده | داده‌ی staging | مالک باید JSON دانلود کند | اجرای `tools/ingest_usda_fdc.py` | مالک | تست‌های FDC موجود |
| 8 | Medium | تغذیه | meals/water/summary کنار گذاشته | لاگ وعده | `x-deferred` | Phase 5 | داده بازبینی‌شده | — |
| 9 | Low | frontend در sandbox | build/typecheck اینجا اجرا نشده | اجرا در CI | sandbox | افزودن job frontend به CI | — | CI سبز |
| 10 | Low | CI | job frontend ندارد | npm test/tsc/build | — | افزودن job | — | CI |

</div>

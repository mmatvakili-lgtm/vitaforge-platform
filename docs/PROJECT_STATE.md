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
| Safety Core | `AUTOMATED_TESTED` | تست‌های backend (۵۵۳ سبز + ۱ skip، حالت in-memory و sqlite) |
| تطابق OpenAPI با مسیرها | `AUTOMATED_TESTED` | Contract Harness هر ۷۸ عملیات را اجرا و پاسخ را با spec می‌سنجد |
| Frontend (مسیرها: home, dashboard, login, register, verify, forgot, reset, onboarding, plan, exercises, exercises/[id], workout, history, nutrition, nutrition/log, nutrition/shopping, foods, profile) | `AUTOMATED_TESTED` | ۴۷ تست Node + e2e با devserver؛ همه‌ی لینک‌ها به صفحه‌ی موجود می‌رسند. اجرای install/tsc/build را مالک روی ویندوز گزارش کرده، در این sandbox اجرا نشده |
| PWA (manifest، آیکون SVG، service worker فقط برای دارایی‌های استاتیک؛ `/api/` و غیر-GET هرگز کش نمی‌شود) | `AUTOMATED_TESTED` | ۲ تست؛ نصب‌پذیری روی مرورگر واقعی بررسی نشده؛ آیکون PNG برای برخی پلتفرم‌ها `PLANNED` |
| ثبت‌نام / ورود / خروج | `AUTOMATED_TESTED` | فقط در devserver و تست |
| تأیید ایمیل | `AUTOMATED_TESTED` | بخش ۴؛ ارسال واقعی SMTP تأیید نشده |
| بازیابی رمز | `AUTOMATED_TESTED` | outbox پایدار؛ SMTP تأیید نشده |
| پایگاه داده | `IMPLEMENTED` | بخش ۳ |
| موتور تمرین + کتابخانه‌ی حرکات (جست‌وجو/فیلتر/صفحه‌بندی) + جایگزینی + ثبت تمرین (ست idempotent، رکورد، توقف به‌خاطر درد) + تاریخچه + داشبورد + نمودار حجم هفتگی (از جلسه‌های ثبت‌شده‌ی خود کاربر) در تاریخچه | `AUTOMATED_TESTED` | e2e روی devserver اجرا شد؛ محتوا فقط `experimental_unreviewed`؛ پیشنهاد progression (فقط پیشنهاد، قابل‌توضیح) روی صفحه‌ی تمرین |
| کاتالوگ حرکات | محتوا بسته | ۳۰ حرکت اولیه، ۰ منتشرشده؛ ۸۷۶ رکورد staging همگی `pending_review` و لایسنس نامعتبر |
| موتور تغذیه + مرور غذا/دستور پخت + لاگ وعده/آب + خلاصه‌ی روز + قیمت کاربر + لیست خرید پایدار + بودجه | `AUTOMATED_TESTED` | بدون غذای بازبینی‌شده → `NEEDS_CONTENT` و مرور خالی؛ آلرژن ذخیره‌شده فیلتر و هشدار می‌دهد و آلرژن نامعلوم ایمن فرض نمی‌شود؛ پروفایل REFER ثبت کالری را می‌بندد؛ داده‌ی وعده/آب/قیمت/لیست خرید پایدار و در erase پاک می‌شود؛ واردکننده‌ی FDC اجرا نشده؛ داده‌ی دستی کاربر با برچسب `user_entered` |
| پروفایل / رضایت‌ها / export / حذف حساب (UI) | `AUTOMATED_TESTED` | صفحه‌ی profile به API‌های موجود وصل است؛ export واقعی (JSON، فقط مالک، ۲۴ ساعت، ۴۱۰ پس از انقضا، شامل تغذیه؛ OPEN-009 بسته) |
| واردسازی FDC (`manage.py import_foods`، همه `pending_review`، بدون بازنویسی رکوردهای موجود) + صف بازبینی غذا (API: `GET /admin/foods`، `POST /admin/foods/{id}/review`) | `AUTOMATED_TESTED` | فقط نقش `nutrition_reviewer`/admin؛ تأیید فقط وقتی `approval_blockers` خالی باشد (منبع، مجوز تأییدشده، آلرژن معلوم، انرژی، اعتبارسنجی، غیر-fixture)؛ آلرژن و مجوز با «تأیید صریح بازبین» ثبت می‌شود (آلرژن: nutrition_reviewer/admin؛ مجوز: فقط admin)؛ رد/بازنشستگی با دلیل؛ بازبین در audit ثبت می‌شود؛ هیچ تأیید خودکاری نیست؛ UI: صفحه‌ی `/[locale]/admin/review` (فقط کارکنان؛ بدون لینک در ناوبری)؛ خود تصمیم‌ها همچنان به متخصص واقعی نیاز دارند |
| ارائه‌دهنده‌ی AI | `PLANNED` | فقط `StubProvider` |
| پرداخت/اشتراک | `PLANNED` | `PaymentProvider` غیرفعال |
| پشتیبان‌گیری/بازیابی | `IMPLEMENTED` (روی SQLite تست خودکار؛ Django/PostgreSQL تأیید نشده) | `manage.py backup_db --out f.json` و `restore_db --in f.json [--replace --yes]`؛ فایل JSON با checksum، مجوز 0600، بدون بازنویسی؛ نشست‌ها در پشتیبان نیست؛ رمزنگاری فایل با مالک (فایل حاوی داده‌ی سلامت است)؛ بازیابی فقط روی دیتابیس خالی مگر `--replace --yes`؛ تست‌ها `persistence/tests/test_backup.py` |

## ۳. پایگاه داده و ماندگاری

- همه‌ی داده در یک KV store (`PersistentStore`) ذخیره می‌شود؛ زیر Django از `apps/core/kv_backend.py` و `DATABASE_URL` (با `dj_database_url`) استفاده می‌کند. هر درخواست App و store تازه می‌سازد.
- SQLite یا PostgreSQL فقط با `DATABASE_URL` تعیین می‌شود. `.env.example`، compose و CI روی PostgreSQL‌اند؛ مالک با SQLite کار می‌کند. ماندگاری بین ری‌استارت روی PostgreSQL در CI آزمون می‌شود (job `django-store`)؛ روی SQLite ویندوز توسط مالک تأیید نشده (`VITAFORGE_TEST_STORE=django`).
- مهاجرت‌ها: CI `makemigrations --check` اجرا می‌کند.

## ۳-پ. روش توسعه و CI (از ۱۳ نوامبر ۲۰۲۶)

- توسعه به‌صورت دسته‌های منسجم روی شاخه‌ی feature؛ ادغام در `main` فقط پس از تست‌های محلی سبز و (در صورت دسترسی) CI سبز. `main` شاخه‌ی استقرار است.
- CI (`.github/workflows/ci.yml`) پنج job دارد: `backend` (حافظه + sqlite، drift تولید OpenAPI/کلاینت، lint مستندات)، `django-postgres` (makemigrations --check + کل تست‌ها روی PostgreSQL ۱۶ و Django)، `frontend` (`tsc --noEmit`، تست Node، `next build`)، `e2e` (سرور HTTP واقعی + کلاینت فرانت + Playwright)، `security` (`pip-audit`، `npm audit` سطح high، اسکن secret).
- **نتیجه‌ی واقعی CI** (commit `942faaf`، شاخه‌ی `feature/ci-e2e`): هر پنج job سبز. یعنی برای اولین بار اجرای واقعی Django + PostgreSQL، `tsc` و `next build` (Next 16.4.6) تأیید شد.
- e2e: `backend/e2e/test_live_http.py` همان کلاینت تایپ‌شده‌ی فرانت (`frontend/scripts/e2e-flow.ts`) را روی سرور HTTP واقعی اجرا می‌کند: ثبت‌نام، تأیید تلگرام (بات **mock**؛ توکن تک‌مصرف واقعی)، onboarding، رضایت، غربالگری، برنامه‌ی تمرین، ثبت تمرین، تغذیه، قیمت‌ها، داشبورد، سناریوی REFER و خروج. تست‌های ایمنی/دسترسی در `contract/tests` و `e2e/test_scenarios.py`.
- تفکیک: بات تلگرام و ایمیل در همه‌ی تست‌ها mock/capture هستند؛ هیچ تست با سرویس خارجی واقعی وجود ندارد.
- اصلاح یافته‌ی CI: افزایش شمارنده‌ی ID در PostgreSQL بیرون از تراکنش خطا می‌داد (۲۷ تست)؛ اکنون تراکنش کوتاه خودش را باز می‌کند.

## ۳-ب. تأیید حساب با تلگرام (کانال اصلی)

وضعیت: `IMPLEMENTED` + `AUTOMATED_TESTED`؛ بات واقعی و Django اجرا نشده. جزئیات، API، متغیرها و دستورهای محلی: `docs/TELEGRAM_VERIFICATION.md`. ایمیل کانال دوم باقی است.

## ۴. ایمیل (میلستون ۱)

وضعیت: `IMPLEMENTED` + `AUTOMATED_TESTED` (۵۲۸ تست backend، حالت in-memory و sqlite؛ فایل `mailer/tests/test_account_mail.py`). `SMTP_CONFIGURED`: خیر. `REAL_EMAIL_DELIVERY_VERIFIED`: خیر. `RUNTIME_VERIFIED`: فقط e2e با devserver و آداپتور capture؛ Django/PostgreSQL در این sandbox اجرا نشده.

**معماری**
- پورت `MailSender` (`backend/mailer/ports.py`) با دو آداپتور: `SmtpSender` (smtplib، STARTTLS/SSL، timeout) و `CaptureSender` (فقط توسعه؛ `delivered=False`، وضعیت outbox برابر `captured` و هرگز `sent`).
- outbox پایدار روی همان KV store (کلکسیون `outbox`؛ بدون مهاجرت جدید). وضعیت‌ها: `pending → processing → sent | captured | retry_scheduled → failed | expired`. claim با قفل ردیف و lease ۳۰۰ ثانیه؛ backoff نمایی (۶۰، ۱۲۰، ۲۴۰… تا سقف ۳۶۰۰ ثانیه) حداکثر ۶ تلاش؛ پیام پس از انقضای توکن یا جایگزینی هرگز ارسال نمی‌شود؛ گیرنده و nonce در وضعیت نهایی پاک می‌شوند.
- توکن‌ها: کد ۶ رقمی و توکن بازیابی ۲۵۶ بیتی از `nonce` تصادفی با HMAC کلید سرور مشتق می‌شوند؛ فقط hash (SHA-256) در DB و فقط nonce در outbox ذخیره می‌شود؛ مقدار خام هیچ‌جا ذخیره یا لاگ نمی‌شود (مگر در کلکسیون صریح `captured_mail` در حالت capture). مقایسه با `hmac.compare_digest`. تک‌مصرف، انقضای ۳۰ دقیقه، جایگزینی توکن قبلی با درخواست جدید، حداکثر ۵ حدس اشتباه برای کد. چرخش `DJANGO_SECRET_KEY` پیام‌های ارسال‌نشده را بی‌اثر می‌کند.
- API: `POST /auth/verify/resend` (API-AUTH-009، ۶۰ عملیات)؛ rate limit با cooldown ۶۰ ثانیه و سقف ۵ در ساعت به ازای ایمیل، مستقل از وجود حساب (۴۲۹)؛ پاسخ ۲۰۲ برای ایمیل ناشناخته و شناخته یکسان است.
- `DEBUG` دیگر تأیید را دور نمی‌زند؛ `auto_verify` حذف شد. ثبت‌نام همیشه حساب تأییدنشده می‌سازد.
- Frontend: صفحه‌های `verify` (ارسال مجدد + شمارنده)، `forgot`، `reset`، پیوند فراموشی رمز در login؛ fa/en.

**پیکربندی** (`.env.example`): `MAIL_PROVIDER` = `smtp` | `capture` | `disabled`. production فقط `smtp` را می‌پذیرد و بدون آن راه‌اندازی شکست می‌خورد («`SMTP is not configured`»). `capture` فقط با `DJANGO_DEBUG=true`. بدون `MAIL_PROVIDER` در debug حالت `disabled` است: چیزی ارسال نمی‌شود و ادعایی هم نمی‌شود.

**گردش کار توسعه**
1. `.env`: `DJANGO_DEBUG=true`، `MAIL_PROVIDER=capture`.
2. ثبت‌نام؛ سپس `python manage.py show_captured_mail --to you@example.com` کد را نشان می‌دهد (در devserver مسیر فقط‌توسعه `GET /api/v1/dev/captured-mail` وجود دارد که فقط با capture+debug ثبت می‌شود).

**راه‌اندازی SMTP (نیازمند اعتبار مالک)**
1. مقادیر `SMTP_*` و `MAIL_FROM_*` را در `.env` بگذارید (`MAIL_PROVIDER=smtp`).
2. `python manage.py mail_status --send-test you@example.com` یک پیام آزمایشی واقعی می‌فرستد؛ فقط پس از رسیدن آن به صندوق می‌توان `REAL_EMAIL_DELIVERY_VERIFIED` گفت.
3. worker: `python manage.py process_outbox --loop` (در compose سرویس `mail-worker`). بدون worker پیام‌ها `pending` می‌مانند.

**محدودیت‌های شناخته‌شده**: rate limit فقط بر اساس ایمیل (نه IP)؛ کلیدهای limiter برای ایمیل‌های ناشناخته پاک‌سازی دوره‌ای ندارند؛ تفاوت زمان پاسخ بین ایمیل شناخته/ناشناخته بررسی نشده؛ ثبت‌نام مجدد با ایمیل موجود پیام نمی‌فرستد؛ مسیر Django/PostgreSQL (قفل ردیف `select_for_update`) در این sandbox اجرا نشده و باید روی ماشین مالک تأیید شود؛ SQLite نویسنده‌ها را سریال می‌کند و PostgreSQL با قفل ردیف؛ رفتار claim در تست‌ها فقط روی in-memory و SQLite فایل‌محور سنجیده شده.

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
| 1 | Critical → Mitigated | ایمیل | کد در کد برطرف شد (بخش ۴) | — | — | — | ارسال واقعی منتظر اعتبار SMTP؛ `mail_status --send-test` |
| 2 | Critical | کاتالوگ حرکات | ۰ حرکت منتشرشده؛ برنامه‌ها `experimental_unreviewed` | فقط حرکات بازبینی‌شده | نبود بازبینی متخصص/لایسنس | ابزار بازبینی ادمین؛ ماندن Pending Review | متخصص | تست دروازه‌ی انتشار (موجود) + UI بازبینی |
| 3 | High | `.env`/DB | مالک SQLite دارد؛ مسیر PostgreSQL فقط در CI | مسیر PostgreSQL مستند و تأییدشده | — | دستور اجرا و بررسی ری‌استارت | — | تست ماندگاری روی PG |
| 4 | High | حریم خصوصی | export/delete، backup/restore ناموجود | موجود و تست‌شده | پیاده‌سازی نشده | Phase 1 | — | تست export/delete/restore |
| 5 | Medium | rate limiting | فقط برای ایمیل (resend/reset)؛ login/register بدون محدودیت نرخ جدا | محدودیت نرخ برای همه‌ی auth | — | Phase 8 | — | تست ۴۲۹ |
| 6 | Medium | `ai_gateway` | فقط Stub | provider واقعی پشت بازبینی حریم | OPEN-002/004 | Phase 6 | بازبینی حقوقی | — |
| 7 | Medium | نگهداری FDC | واردکننده اجرا نشده | داده‌ی staging | مالک باید JSON دانلود کند | اجرای `tools/ingest_usda_fdc.py` | مالک | تست‌های FDC موجود |
| 8 | Medium | تغذیه | meals/water/summary کنار گذاشته | لاگ وعده | `x-deferred` | Phase 5 | داده بازبینی‌شده | — |
| 9 | Low | frontend در sandbox | build/typecheck اینجا اجرا نشده | اجرا در CI | sandbox | افزودن job frontend به CI | — | CI سبز |
| 10 | Low | CI | job frontend ندارد | npm test/tsc/build | — | افزودن job | — | CI |

</div>

# سند ۱۵ — Security & Privacy Specification

| فیلد | مقدار |
|---|---|
| Document ID | DOC-15 |
| Version | 0.1 |
| Status | Draft — Complete (فنی)؛ **بررسی حقوقی/قانونی: Pending Legal Review (OPEN-004، EXP-010، EXP-012)** |
| Created / Updated | 2026-11-07 |
| Owner | Security & Privacy Engineer |
| Related Documents | DOC-03، DOC-05، DOC-08 |
| Related Decisions | DEC-004، 111، 112، 125؛ ADR-0004؛ EXP-010/012 |

> این سند مشاوره حقوقی نیست. هیچ ادعای انطباق (GDPR/قوانین بازار) اعلام نمی‌شود؛ فقط کنترل‌های فنی.

## 1. دارایی‌ها و طبقه‌بندی
| کلاس | نمونه | کنترل |
|---|---|---|
| C3 (سلامت/حساس) | health_conditions، symptom/pain، تاریخ تولد، عکس بدن | رمزنگاری سطح اپ برای فیلدهای متنی آزاد، رضایت، ممیزی دسترسی، بدون ارسال خارجی، عدم کش، no-store |
| C2 (شخصی) | ایمیل، موبایل، اندازه‌ها، لاگ تمرین | رمزنگاری در حالت ذخیره (دیسک)، RBAC |
| C1 (عملیاتی) | کاتالوگ، پیکربندی | استاندارد |

## 2. مدل تهدید (STRIDE خلاصه)
| تهدید | نمونه | کنترل |
|---|---|---|
| Spoofing | سرقت نشست | کوکی HttpOnly/Secure/SameSite، ابطال نشست، rate limit، قفل حساب |
| Tampering | تغییر محدودیت/نسخه قواعد | append-only، نسخه immutable، CHECK/Trigger، RBAC |
| Repudiation | انکار تغییر | `audit_logs`، `safety_decisions` |
| Info disclosure | IDOR روی داده سلامت، لاگ PHI | Object-level permission، UUID، no-store، لاگ Redacted، anti-enumeration |
| DoS | brute force، AI abuse | rate limit، سهمیه، timeouts |
| Elevation | ادمین فنی دیدن PHI | `health_data_access_grants` زمان‌دار + ممیزی؛ مجوز نقش‌ها |
| LLM-specific | Prompt injection، نشت | ADR/DOC-08: Redaction، بدون tool، Validator |
| Upload | فایل مخرب | نوع/اندازه، اسکن، ذخیره خارج web root، URL امضاشده |

## 3. احراز هویت و نشست
- Django auth؛ هش رمز Argon2 (در صورت عدم دسترسی PBKDF2-SHA256 با iterations بالا)؛ حداقل طول ۱۰؛ بررسی رمز ضعیف رایج.
- نشست سمت سرور، کوکی `HttpOnly; Secure; SameSite=Lax`؛ CSRF برای متدهای تغییردهنده.
- قفل پس از N تلاش ناموفق (config) با backoff؛ پیام خطای عمومی؛ ثبت `authentication_events` (IP هش‌شده).
- تأیید حساب؛ توکن‌های بازیابی: تصادفی ≥ 128bit، ذخیره‌شده به‌صورت هش، یک‌بارمصرف، انقضا کوتاه؛ پس از تغییر رمز ابطال همه نشست‌ها.
- 2FA: Deferred.

## 4. مجوزدهی
RBAC (نقش‌ها DOC-03 §8) + Object-level (queryset فیلتر مالک)؛ پیش‌فرض deny؛ تست ماتریس مجوز خودکار برای هر endpoint (`API-*`).
- **داده سلامت:** نیازمند `consent(health_data)` معتبر + مالکیت؛ ادمین فقط با grant.
- **Mass assignment:** Serializerها فهرست سفید صریح؛ فیلدهای متخصص‌محور (`professional_*`, `status`, `source`) توسط کاربر قابل‌نوشتن نیستند.

## 5. محافظت داده
- TLS 1.2+؛ HSTS؛ رمزنگاری دیسک/DB در لایه زیرساخت؛ **رمزنگاری سطح اپ** (AES-GCM یا Fernet، کلید از Secret Manager/ENV) برای `aggravating_factors`، `relieving_factors`، `professional_*`، `note_enc` (ADR-0008 برنامه‌ریزی‌شده)؛ چرخش کلید با `key_id` در ciphertext.
- Backup رمزنگاری‌شده؛ تست بازیابی دوره‌ای.
- **Redaction لاگ:** فهرست ممنوع فیلدها؛ تست اسکن لاگ‌ها در CI؛ Sentry-like: scrubbing پیش‌فرض.
- حداقل‌سازی: فقط فیلدهای لازم Safety Core جمع‌آوری شود؛ `sex` اختیاری.

## 6. حریم خصوصی و حقوق کاربر
| حق | پیاده‌سازی |
|---|---|
| دسترسی/اصلاح | PG-PRIV/Profile/Health |
| خروجی | `POST /privacy/export` ← job ← JSON با لینک امضاشده زمان‌دار |
| حذف | حذف نرم فوری + حذف سخت پس از پنجره (DEC-112، پیش‌فرض ۳۰ روز، پیکربندی)؛ `audit_logs` ناشناس‌سازی (کاربر→NULL، فراداده بدون PHI) |
| لغو رضایت | توقف پردازش سلامت؛ حفظ داده تا درخواست حذف (یا حذف طبق انتخاب) |
| عدم استفاده تبلیغاتی | ممنوع؛ هیچ SDK تبلیغاتی/آنالیتیکس شخص‌ثالث روی داده سلامت |
متن‌ها/مبنای قانونی/نگهداری: Pending Legal Review.

## 7. آفلاین (ADR-0004)
- داده درد/علائم/سلامت: هرگز در حافظه مرورگر (IndexedDB/localStorage/SW cache) ذخیره نمی‌شود؛ پاسخ‌های API سلامت `Cache-Control: no-store`.
- Service Worker: فقط Shell و دارایی‌های ایستا؛ API سلامت هرگز cache نمی‌شود.
- `offline_workout_log` (پیش‌فرض خاموش): فقط ست‌های غیرحساس؛ WebCrypto AES-GCM؛ کلید مشتق از نشست، در حافظه (نه storage)؛ پاک‌سازی هنگام خروج/انقضا؛ `client_uuid` برای idempotency. فعال‌سازی نیازمند بازبینی امنیتی و ثبت در Decision Register.

## 8. امنیت اپلیکیشن
CSP سخت (بدون inline)؛ XSS: escaping پیش‌فرض React/DRF؛ SQLi: ORM/پارامتری؛ SSRF: بدون fetch URL کاربر؛ headers (X-Content-Type-Options، Referrer-Policy، Permissions-Policy، frame-ancestors none)؛ CORS فهرست سفید؛ rate limit سراسری+سخت‌گیر برای auth/AI/export؛ اعتبارسنجی ورودی سمت سرور؛ خطای عمومی (بدون stack trace)؛ Secret ها فقط ENV/Secret Manager (`.env.example` ساختگی)؛ pre-commit secret scan.
## 9. زنجیره تأمین
قفل وابستگی (`uv.lock`/`package-lock`)، SCA در CI (pip-audit/npm audit)، Dependabot-like بروزرسانی، SBOM، حداقل وابستگی.
## 10. مدیریت رخداد
شناسایی (Alert)، تفکیک، اطلاع‌رسانی بر اساس الزام حقوقی بازار (Pending Legal)، پس‌از‌حادثه. Runbook در DOC-17.
## 11. ممیزی
`audit_logs`: دسترسی/تغییر داده سلامت توسط غیرمالک، grantها، انتشار قواعد/حرکات، تغییر پلن/نقش، export/delete. غیرقابل ویرایش (REVOKE UPDATE/DELETE برای نقش اپ).
## 12. معیارهای پذیرش
| ID | معیار |
|---|---|
| AC-SEC-001 | تست مجوز: هر endpoint بدون احراز 401، کاربر دیگر 404/403 |
| AC-SEC-002 | IDOR: کاربر A نمی‌تواند رکورد سلامت B را بخواند/بنویسد |
| AC-SEC-003 | mass assignment فیلدهای متخصص رد می‌شود |
| AC-SEC-004 | لاگ‌ها/پاسخ‌ها فاقد PHI در تست اسکن |
| AC-SEC-005 | Response سلامت `no-store` |
| AC-SEC-006 | export فقط داده خود کاربر |
| AC-SEC-007 | CSRF بدون توکن رد می‌شود |
| AC-SEC-008 | rate limit ورود فعال |
| AC-SEC-009 | هیچ Secret واقعی در repo (secret scan) |

<div dir="rtl">

# ADR-0009 — مدل نشست و احراز هویت وب

| فیلد | مقدار |
|---|---|
| Status | Accepted (پیاده‌سازی Django: Not Run) |
| Date | 2026-11-09 |
| Owner | Architect |
| Related | DEC-152، ADR-0007، DOC-07 |

## وضعیت فعلی (بررسی‌شده)

- **Spec و devserver:** cookie `sessionid` (HttpOnly) + هدر `X-CSRFToken` (double-submit با cookie `csrftoken`). Cookie با `Secure` در تولید و انقضای ۱۴ روز.
- **Django فعلی:** `BearerTokenAuthentication` روی جدول `ApiSession` (hash ذخیره می‌شود). بدون cookie و بدون CSRF؛ با spec ناسازگار است.
- **سرویس دامنه (`identity.py`):** توکن مات، hash با SHA-256، `exp` مطلق ۱۴ روزه، `revoked`، لغو همه نشست‌ها پس از بازنشانی گذرواژه.

## گزینه‌ها

- A) Bearer در `localStorage`/JS: در برابر XSS آسیب‌پذیر؛ با spec ناسازگار.
- B) `django.contrib.sessions`: دو مالک برای نشست (Django و `IdentityService`)؛ لغو/فهرست نشست‌ها دوبار پیاده می‌شود.
- C) **cookie HttpOnly حاوی همان توکن مات `IdentityService` + CSRF double-submit.**

## تصمیم: C

1. `IdentityService` تنها مالک نشست است؛ Django فقط transport است: `CookieSessionAuthentication` توکن را از cookie `sessionid` می‌خواند و `identity.session_of(token)` را صدا می‌زند.
2. Cookie: `HttpOnly`، `Secure` (جز dev)، `SameSite=Lax`، `Path=/`، `Max-Age` برابر باقی‌مانده TTL.
3. CSRF برای هر متد غیرایمن اجباری و صریح است (DRF `SessionAuthentication` استفاده نمی‌شود، پس بررسی دستی لازم است): مقایسه ثابت‌زمان cookie `csrftoken` با هدر `X-CSRFToken`؛ مسیرهای بدون نشست (`register`، `login`، reset) نیز Origin/Referer را بررسی می‌کنند.
4. **Bearer از قرارداد وب حذف می‌شود.** در devserver فقط برای Harness باقی می‌ماند و برچسب DEV دارد؛ Harness باید نقل‌وانتقال cookie داشته باشد تا همان رفتار Django را بسنجد.
5. TTL مطلق ۱۴ روز؛ `seen` فقط برای نمایش فهرست نشست‌ها؛ idle timeout تصمیم باز است (Open).
6. Logout: لغو سمت سرور + پاک‌کردن cookie. Revocation: لغو یک نشست توسط خود کاربر؛ لغو همه نشست‌ها پس از بازنشانی گذرواژه و تغییر گذرواژه.
7. Password reset: توکن یک‌بار‌مصرف، فقط hash ذخیره، انقضا (۴۱۰ پس از انقضا)، گذرواژه ضعیف توکن را نمی‌سوزاند، پاسخ درخواست عمومی (ضد enumeration).
8. قفل حساب و rate limit مطابق spec (429)؛ پیاده‌سازی `rate limit Django Not Run.`

## پیامد

- تغییر لازم: `apps/core/auth.py` و `settings.py` (حذف Bearer، افزودن cookie/CSRF)، `contract.harness` (گزینه cookie)، مدل `ApiSession` (فیلدهای `exp`, `seen`, `device`).
- تست پذیرش: Harness روی Django با cookie؛ تست منفی CSRF (بدون هدر 403)، cookie بدون `HttpOnly`/`Secure` رد، نشست لغوشده 401، انقضا 401.

</div>

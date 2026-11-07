<div dir="rtl">

# MVP_SCOPE

| فیلد | مقدار |
|---|---|
| Document ID | DOC-MVP |
| Version | 0.1 |
| Status | Draft — Complete |
| Updated | 2026-11-07 |
| Related | DOC-01 §3.1، DOC-18، DEC-132 |

## تعریف
کوچک‌ترین نسخه‌ای که ارزش واقعی (برنامه تمرین ایمن + ثبت + پیشرفت) را ارائه می‌کند، با Safety Core مستقل از LLM.

## داخل MVP (Phase 1)
Identity (ثبت‌نام/ورود/نشست/بازیابی)؛ Profile/i18n (فارسی/انگلیسی، شمسی/میلادی)؛ Consent/Privacy (export/delete)؛ Onboarding؛ Body measurements پایه؛ Health Records (درد/محدودیت)؛ **Safety Core** + Audit؛ Exercise Catalog + گردش بازبینی؛ Workout Engine قاعده‌محور؛ Workout Logging + تاریخچه؛ Dashboard؛ AI Gateway (زیرساخت، LLM خاموش، Stub)؛ Subscription (Free + Feature Gating + Port پرداخت)؛ Admin پایه.

## بیرون MVP (Deferred، حذف نشده)
تغذیه/غذا/بودجه/مکمل؛ رشته‌های ورزشی؛ RAG/Coach؛ تحلیل پیشرفته؛ اتصال دستگاه؛ تصویر/حرکت؛ پنل متخصص؛ جامعه؛ پرداخت واقعی؛ مسیر C.

## «تعریف انجام» برای MVP (Exit Criteria)
1. همه US های P0 با تست سبز (گزارش واقعی؛ `Not Run` ممنوع برای P0 در release).
2. ST-001..ST-017 سبز؛ AC-SAF-* سبز.
3. هیچ محتوای بالینی `draft_unreviewed` برای کاربر واقعی منتشر نشود (یا Reviewer تأیید کرده باشد).
4. بررسی امنیتی پایه (AC-SEC-*)؛ دو زبان کامل؛ a11y پایه.
5. دستورالعمل نصب/اجرا، `.env.example`، OpenAPI.

## وضعیت واقعی فعلی
مستندات: کامل. کد: شروع نشده/در حال شروع Safety Core (ADR-0007). **هیچ قابلیتی هنوز Complete نیست.**

</div>

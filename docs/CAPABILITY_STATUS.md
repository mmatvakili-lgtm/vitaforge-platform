<div dir="rtl">

# CAPABILITY_STATUS — وضعیت واقعی قابلیت‌ها

| فیلد | مقدار |
|---|---|
| Document ID | DOC-CAP |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-08 |

راهنما: ✔ انجام‌شده، ◐ جزئی/نمونه، ✖ انجام‌نشده. این وضعیت‌ها جدا هستند: پیاده‌سازی ≠ تست‌شدن ≠ داده ≠ اعتبارسنجی ≠ آماده تولید ≠ تأیید تخصصی. ستون «`Pending Expert Review`» یعنی بدون بازبینی متخصص قابل‌اتکا نیست (✔ = هنوز منتظر بازبینی).

| ماژول | Designed | Implemented | Tested | Data Populated | Validated | Production Ready | `Pending Expert Review` | یادداشت |
|---|---|---|---|---|---|---|---|---|
| Safety Core (موتور + قواعد ساختاری) | ✔ | ✔ | ✔ | ◐ | ✖ | ✖ | ✔ | قواعد بالینی R1xx..R5xx `Draft`؛ پارامتر احتیاط `Pending Expert` |
| Safety Core: توضیح تصمیم | ✔ | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | متن‌ها بازبینی زبانی/بالینی نشده |
| Exercise Schema + Import Pipeline | ✔ | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | Importer برای free-exercise-db؛ بدون مجوز تأییدشده |
| Exercise Database (محتوا) | ✔ | ✔ | ✔ | ◐ | ✖ | ✖ | ✔ | ۳۰ حرکت `experimental`، نمونه، بدون منبع علمی؛ ۵ حرکت کششی با `safety_tags_status=missing` |
| Workout Engine | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | ✔ | پارامترها `Unverified` (EXP-013) |
| Progression & Recovery | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | ✔ | آستانه‌ها پیش‌فرض مهندسی |
| Nutrition Engine | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | ✔ | ضرایب/بازه‌ها `Unverified` (EXP-006)؛ بانک غذا ندارد |
| `AI Decision Layer` | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | ✔ | Provider واقعی ندارد؛ KB خالی/نمونه |
| API (آداپتور توسعه) | ✔ | ✔ | ✔ | ✖ | ✔ | ✖ | ✖ | ۵۶/۵۶ مسیر با Contract Harness اعتبارسنجی‌شده (فقط devserver)؛ شکاف‌ها در OPEN-011 |
| API/ORM Django | ✔ | ✔ | ✖ | ✖ | ✖ | ✖ | ✖ | wsgi + KV backend + migration + ۵۶ عملیات از طریق App مشترک؛ `Not Run` (Django نصب‌پذیر نبود؛ DEC-150) |
| لایه پایداری (SQLite) | ✔ | ✔ | ✔ | ✔ | ✖ | ✖ | ✔ | ماندگاری پس از restart، rollback، ایزولاسیون، حذف حساب روی فایل SQLite |
| Publication Gate حرکات | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | ✔ | سرویس + Bridge + Loader + CheckConstraint (Not Run)؛ بدون Published |
| Frontend Next.js | ✔ | ◐ | ✖ | ✖ | ✖ | ✖ | ✖ | اسکلت، `Not Run`؛ UI آزمایشی ساده اجراشده |
| Identity/Consent/Privacy | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | ◐ | متن‌های حقوقی `Pending Legal` |
| Subscriptions/Entitlements | ✔ | ✔ | ✔ | ✖ | ✖ | ✖ | ✖ | پرداخت غیرفعال |
| E2E سناریوهای واقعی | ✔ | ✔ | ✔ | ✖ | ◐ | ✖ | ✖ | ۸ سناریو روی محتوای نمونه؛ سناریوی کاربر واقعی انجام نشده |

«Production Ready» برای هیچ ماژولی ✔ نیست و تا بسته‌شدن موانع `OPEN-001..008` نخواهد بود.

</div>

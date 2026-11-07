<div dir="rtl">

# RELEASE_CHECKLIST — وضعیت واقعی MVP

| فیلد | مقدار |
|---|---|
| Document ID | DOC-REL |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-07 |

| مورد | وضعیت | شواهد |
|---|---|---|
| هسته ایمنی، موتور تمرین، AI Gateway، Entitlement، سرویس‌های کاربردی | `Passed` | `cd backend && python3 -m pytest -q` ← ۱۸۹ تست سبز |
| API توسعه (WSGI) + UI آزمایشی | `Passed` (فقط توسعه) | تست HTTP + اجرای واقعی `python3 -m devserver` |
| آداپتور Django/DRF + مهاجرت‌ها | `Not Run` | کد نوشته شده؛ Django نصب نیست |
| Next.js | `Not Run` | کد نوشته شده؛ `npm install` ممکن نیست |
| Docker/CI | `Not Run` | فایل‌ها نوشته شده |
| محتوای بالینی (حرکات، قواعد R1xx..R5xx، مسیر B فعال) | `Blocked` | `OPEN-003`، `EXP-001..013` |
| بررسی حقوقی و ارسال داده سلامت به AI | `Blocked` | `OPEN-002`، `OPEN-004` |
| پرداخت | `Blocked` | `OPEN-001`، `OPEN-005` (`PaymentProvider` غیرفعال) |

انتشار برای کاربر واقعی ممنوع است تا `Blocked`ها بسته شوند.

</div>

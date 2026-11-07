<div dir="rtl">

# IMPLEMENTATION_PLAN

| فیلد | مقدار |
|---|---|
| Document ID | DOC-IMPL |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-07 |
| Related | DOC-18، ADR-0007، DOC-16 |

وضعیت‌ها: `Complete` فقط با کد + تست اجراشده سبز. سایر: `Written-NotRun`، `In Progress`، `Not Started`، `Blocked`.

| M | وضعیت | یادداشت |
|---|---|---|
| M1 Foundation | In Progress | ساختار repo، `.env.example`، README؛ Docker/CI فایل‌ها نوشته‌شده، Not Run |
| `M4 Safety Core` | Complete (engine) | ۷۲ تست pytest سبز؛ پوشش خطی ≈۹۶٪ (engine)؛ محتوای بالینی همچنان `Pending Expert`؛ کدهای `SAF-R013..R018` در سند ۰۹ ثبت شدند |
| `M6a Workout Engine` (domain) | Complete (engine) | تولید برنامه، پیشرفت، Deload؛ ۳۲ تست سبز؛ پارامترها `Unverified` (EXP-013) و برچسب `experimental` |
| M2 Identity | Not Started | نیازمند Django |
| M3 Profile/Onboarding/Health | Not Started | |
| M5 Catalog | Not Started | |
| M6b Workout API | Not Started | |
| M7 Logging/Dashboard | Not Started | |
| `M8 AI Gateway` | Not Started | دامنه خالص قابل‌اجرا (Redactor/Validator) |
| M9 Subscription/Admin | Not Started | منطق Entitlement دامنه خالص قابل‌اجرا |
| M10 Release | Not Started | |

## ادامه کار (Resume)
`cd backend && python3 -m pytest -q` برای تست‌های دامنه؛ سپس ادامه از اولین `Not Started` در جدول. محدودیت: Django/DRF/Next.js/Playwright در محیط نصب نیست (شبکه بسته) — کد آن‌ها نوشته شده ولی `Not Run`.

</div>

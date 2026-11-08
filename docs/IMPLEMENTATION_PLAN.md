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
| M1 Foundation | Complete (جز اجرای Docker/CI) | ساختار repo، `.env.example`، اعتبارسنجی env با ۱۰ تست؛ `docker-compose`/CI نوشته‌شده، `Not Run` |
| `M4 Safety Core` | Complete (engine) | ۷۲ تست pytest سبز؛ پوشش خطی ≈۹۶٪ (engine)؛ محتوای بالینی همچنان `Pending Expert`؛ کدهای `SAF-R013..R018` در سند ۰۹ ثبت شدند |
| `M6a Workout Engine` (domain) | Complete (engine) | تولید برنامه، پیشرفت، Deload؛ ۳۲ تست سبز؛ پارامترها `Unverified` (EXP-013) و برچسب `experimental` |
| M2 Identity | Complete (service) | ثبت‌نام/ورود/نشست/قفل‌شدن با `scrypt`؛ آداپتور Django/ORM `Not Started` |
| M3 Profile/Onboarding/Health | Complete (service) | رضایت append-only، مراحل Onboarding، ورودی سلامت → `SafetyRequest`؛ آداپتور Django `Not Started` |
| M5 Catalog | Complete (service + dev adapter) | چرخه `draft→published→retired` با نقش‌های جدا؛ نمونه‌ها هرگز منتشر نمی‌شوند؛ ۸ تست |
| `M6b Workout API` | Complete (service + dev adapter) | تولید/جایگزینی/نسخه‌بندی؛ API روی WSGI توسعه؛ DRF `Not Started` |
| M7 Logging/Dashboard | Complete (service + dev adapter) | ثبت ست/پایان جلسه/پیشرفت هفتگی؛ داشبورد کامل `Not Started` |
| `M8 AI Gateway` | Complete (domain) | Pipeline، Intent/Context/Redactor، Validator، StubProvider، `PolicyViolation`؛ ۱۷ تست؛ ادغام Django/Provider واقعی `Not Started` |
| M9 Subscription/Admin | In Progress | منطق Entitlement (دامنه) Complete با ۴ تست؛ مدل/`API/Admin Not Started` |
| M10 Release | In Progress | `Dockerfile`/`docker-compose`/CI و اسکلت Django/Next.js نوشته شد، `Not Run`؛ گزارش نهایی و `RELEASE_CHECKLIST` در انتظار |

## دستور تکمیل منطق محصول و داده (۲۰۲۶-۱۱-۰۸)
| مورد | وضعیت |
|---|---|
| ۱ Exercise Schema + Import | Implemented + Tested |
| ۲ مجموعه اولیه حرکات | ۲۵ حرکت `experimental`، منبع علمی ندارد، `Pending Expert` |
| ۳ Safety Core (توضیح، تجهیزات، سطح) | Implemented + Tested |
| ۴ Workout Engine (ترتیب، تعادل، ریکاوری، تنوع) | Implemented + Tested، پارامترها `Unverified` |
| ۵ Progression & Recovery | Implemented + Tested |
| ۶ Nutrition Engine | Implemented + Tested (تخمین؛ هدف عددی غیرفعال) |
| ۷ `AI Decision Layer` | Implemented + Tested |
| ۸ اتصال API | آداپتور توسعه کامل؛ Django/Next.js `Not Run` |
| ۹ E2E | ۸ سناریو روی محتوای نمونه |
| ۱۰ مستندسازی | `DECISION_REGISTRY`، `CAPABILITY_STATUS`، `10A` |

اعلام «MVP کامل» مجاز نیست: داده بازبینی‌شده، اتصال واقعی Frontend/Backend (Django/Next.js اجراشده) و تأیید تخصصی وجود ندارد. جزئیات: `CAPABILITY_STATUS.md`.

## ادامه کار (Resume)
`cd backend && python3 -m pytest -q` برای تست‌های دامنه؛ سپس ادامه از اولین `Not Started` در جدول. محدودیت: Django/DRF/Next.js/Playwright در محیط نصب نیست (شبکه بسته) — کد آن‌ها نوشته شده ولی `Not Run`.


## اجرای نسخه توسعه
`cd backend && python3 -m devserver` سپس `http://127.0.0.1:8000`. فقط توسعه: داده موقت، حرکات نمونه (`demo_*`)، بدون محتوای بالینی. آداپتور تولیدی طبق ADR-0001 Django/DRF است و هنوز نوشته نشده.

</div>

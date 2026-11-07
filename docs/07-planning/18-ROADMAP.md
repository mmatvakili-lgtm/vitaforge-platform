# سند ۱۸ — Development Roadmap

| فیلد | مقدار |
|---|---|
| Document ID | DOC-18 |
| Version | 0.1 |
| Status | Draft — Complete؛ بدون تاریخ تقویمی (OPEN-006) |
| Created / Updated | 2026-11-07 |
| Owner | Product Owner / Architect |
| Related Documents | DOC-01، DOC-03، MVP_SCOPE، IMPLEMENTATION_PLAN |
| Related Decisions | DEC-001، 009، 132؛ ADR-0002، ADR-0007 |

## 1. اصول زمان‌بندی
وابستگی‌محور؛ Safety Core پیش از هر قابلیت‌ای که حرکت/برنامه نمایش می‌دهد (ADR-0002)؛ هیچ قابلیتی حذف نمی‌شود، فقط زمان‌بندی (DEC-009). تاریخ‌ها تا اعلام ظرفیت تیم تعیین نمی‌شود.

## 2. فازها (سند مادر §34، اصلاح‌شده)
| فاز | محتوا | تغییر نسبت به سند مادر |
|---|---|---|
| Phase 0 | تحقیق، اسناد، مدل داده، سیاست ایمنی، تصمیم‌ها | — |
| Phase 1 (MVP) | زیرساخت؛ حساب/رضایت/پروفایل/Onboarding؛ سلامت/درد؛ **Safety Core پایه**؛ بانک حرکات؛ Workout Engine قاعده‌محور؛ ثبت تمرین؛ داشبورد؛ AI Gateway (زیرساخت، LLM غیرفعال)؛ اشتراک (Free+Feature Gating)؛ پنل ادمین پایه | Safety Core پایه از Phase 2 به Phase 1 منتقل شد (ADR-0002)؛ AI Gateway زیرساخت اضافه شد |
| Phase 2 | Safety Engine کامل: پایش علائم، ارجاع، جایگزین‌های سازگار، چک‌این؛ مسیر B فعال (پس از EXP-011)؛ مسیر C (پس از EXP-005)؛ تست‌های تخصصی | — |
| Phase 3 | تغذیه، بانک غذا، دستور، جایگزین، بودجه، خرید، مکمل (پس از EXP-006/007) | — |
| Phase 4 | RAG، AI Coach، Validator تکمیلی، ارزیابی؛ رشته‌های ورزشی (مدل‌ها)؛ برنامه تطبیقی | رشته‌های ورزشی از ۵ به ۴ آمد (وابسته به موتور تمرین) |
| Phase 5 | تحلیل پیشرفته، اتصال دستگاه، تحلیل تصویر محدود | — |
| Phase 6 | پنل مربی/متخصص، جامعه، پرداخت بین‌المللی، مقیاس‌پذیری، 2FA | — |

## 3. Milestoneهای Phase 1 (Vertical Slice)
ترتیب نهایی پس از تحلیل وابستگی و محدودیت محیط (ADR-0007): **M4 قبل از M2/M3** برای دامنه خالص.
| M | عنوان | وابستگی | معیار خروج |
|---|---|---|---|
| M1 | Foundation: ساختار repo، Compose، settings، health، logging، CI | — | ساختار + تست پایه + `.env.example` |
| M4 | **Safety Core** (پکیج خالص، قواعد ساختاری، تصمیم، Audit، تست منفی/مرزی) | M1 | AC-SAF-002/003/006؛ branch coverage ≥ ۹۵٪ |
| M6a | Workout Engine دامنه‌ای (بدون Django) + اتصال به SafetyGate | M4 | AC-WO-001..007 |
| M2 | Identity | M1 | AC-SEC-001/007/008؛ US-ACC |
| M3 | Profile & Onboarding & Health Records & Consent | M2، M4 | US-PRO/ONB/HEALTH/PRIV |
| M5 | Exercise Catalog + Admin گردش | M3 | AC-EX-001..005 |
| M6b | Workout API/persistence | M5، M6a | US-WO |
| M7 | Workout Logging + Dashboard | M6b | US-LOG/DASH |
| M8 | AI Gateway | M4 | AC-AI-001..006 |
| M9 | Subscription & Admin | M2 | US-ADM/SUB |
| M10 | Integration & Release (E2E، امنیت، docs) | همه | MVP_SCOPE Exit Criteria |

## 4. Backlog با وابستگی
| قابلیت | فاز | پیش‌نیاز | وضعیت |
|---|---|---|---|
| مسیر B فعال | 2 | EXP-001/002/011 | Pending Specialist Approval |
| مسیر C/پروتکل‌ها | 2+ | EXP-005، DEC-120، OPEN-004 | Blocked |
| تغذیه/بانک غذا/بودجه | 3 | EXP-006، OPEN-007 | Deferred |
| مکمل | 3 | EXP-007 | Deferred |
| RAG/Coach | 4 | ADR-0005 ارزیابی، OPEN-002 | Deferred |
| رشته‌های ورزشی | 4 | EXP-013 مدل‌ها | Deferred |
| تحلیل تصویر/حرکت | 5 | EXP-009، رضایت جدا | Deferred |
| اتصال دستگاه | 5 | رضایت device، حقوقی | Deferred |
| پنل مربی/متخصص | 6 | DEC-120 | Deferred |
| جامعه | 6 | DEC-119 | Deferred |
| پرداخت بین‌المللی | 6 | OPEN-001 | Deferred |

## 5. معیار خروج Phase 0 (DOC-15 Directive)
اسناد ۲۰/۲۰؛ تناقض‌ها بسته؛ ADRها؛ Traceability؛ Index؛ ZIP؛ موارد Pending مشخص.

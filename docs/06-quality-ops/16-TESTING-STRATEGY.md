# سند ۱۶ — Testing Strategy

| فیلد | مقدار |
|---|---|
| Document ID | DOC-16 |
| Version | 0.1 |
| Status | Draft — Complete |
| Created / Updated | 2026-11-07 |
| Owner | QA Lead |
| Related Documents | DOC-02، DOC-09 (ST-*)، DOC-15، DOC-19 |
| Related Decisions | ADR-0006، ADR-0007 |

## 1. سطوح تست
| سطح | ابزار | هدف | اجرا در CI |
|---|---|---|---|
| Unit (دامنه) | pytest | Safety Core، Workout Engine، محاسبات، Redactor، Validator | هر commit |
| Property-based | hypothesis (در صورت نصب؛ وگرنه تولیدکننده سفارشی با seed) | «حرکت منع‌شده هرگز در خروجی نیست»، قطعیت | هر commit |
| Integration (Django) | pytest-django + Postgres | مدل‌ها، migration، سرویس‌ها، ترنزاکشن | هر commit |
| API/Contract | DRF test client + schemathesis/OpenAPI validator | پاسخ‌ها مطابق DOC-07 | هر commit |
| Permission | ماتریس خودکار | endpoint × نقش × مالکیت | هر commit |
| Security | pip-audit، npm audit، bandit، secret scan، تست‌های AC-SEC | | هر commit/شبانه |
| Architecture | import-linter + تست AST | AC-ARCH-*، AC-SAF-001 | هر commit |
| Frontend unit | vitest + Testing Library | کامپوننت‌ها، i18n، تبدیل تاریخ | هر commit |
| Accessibility | axe (playwright) | WCAG | PR |
| E2E | Playwright | جریان‌های کلیدی (فارسی/RTL و انگلیسی/LTR، موبایل/دسکتاپ) | PR/شبانه |
| Visual | Playwright screenshots | Light/Dark × RTL/LTR | PR |
| Performance | k6/locust (پایه) | بودجه NFR-PERF (فرضیه) | شبانه |
| AI Evaluation | harness داخلی | DOC-08 §7 | PR (Stub) |
| Migration | `makemigrations --check`، upgrade/downgrade روی DB تمیز | | هر commit |

## 2. تست‌های ایمنی (اجباری، اولویت بالا)
مجموعه `safety/` شامل سناریوهای ST-001..ST-017 (DOC-09) و:
- **منفی/مرزی:** ورودی ناقص، enum نامعتبر، سن دقیقاً ۱۸ و ۱۷ سال و ۳۶۴ روز، چند محدودیت هم‌زمان، چند ناحیه، محدودیت منقضی، قاعده draft در مجموعه، rule_set بدون published، حرکت بدون ناحیه‌ای از ۱۵ تا، ID ناشناس، ورودی تهی.
- **Fail-safe:** تزریق استثنا در هر مرحله ← `ERROR_FAILSAFE`؛ قاعده با JSON خراب ← fail-safe؛ timeout.
- **قطعیت:** همان ورودی ← همان `inputs_hash` و تصمیم.
- **Property-based:** برای ورودی تصادفی معتبر، هیچ حرکت `blocked` در `allowed`؛ هیچ ALLOW با `consent=false`؛ هیچ ALLOW با هشدار مثبت.
- **اولویت:** تعارض مراحل (مثلاً هشدار + محدودیت) ← بالاترین اولویت.
- **عدم‌دور‌زدن:** تست معماری که هر مسیر ارائه برنامه SafetyDecision می‌گیرد.
- **پوشش:** شاخه‌های `safety_core` ≥ ۹۵٪ (Branch coverage)؛ شکست = Block.

## 3. داده تست
- Factoryها؛ داده sample با برچسب `SAMPLE_UNREVIEWED`؛ هیچ داده کاربر واقعی.
- دیتابیس تست: Postgres (Compose)؛ `Not Run` اگر در دسترس نباشد.
- حساب آزمایشی فقط در dev (فلگ `DEV_SEED`؛ رد در prod).

## 4. شناسه‌گذاری تست
`TST-<MOD>-nnn` (نگاشت در DOC-19). هر تست `@pytest.mark.req("FR-…")` یا docstring ارجاع می‌دهد؛ اسکریپت `tools/trace_check.py` ارجاعات را با DOC-19 مقایسه می‌کند.

## 5. معیارهای خروج Milestone
۱) تست‌های Milestone سبز؛ ۲) migration سالم؛ ۳) هیچ باگ بحرانی باز؛ ۴) پوشش حداقلی (دامنه ≥ ۸۰٪؛ Safety ≥ ۹۵٪ branch)؛ ۵) مستندات به‌روز؛ ۶) گزارش واقعی (Passed/Failed/**Not Run**).

## 6. وضعیت اجرایی (محدودیت محیط، ADR-0007)
| سطح | وضعیت قابل‌اجرا در محیط فعلی |
|---|---|
| Unit دامنه (Safety Core، Workout Engine) | قابل‌اجرا (Python+pytest) |
| Integration/API/Permission Django | **Not Run** تا نصب Django |
| Frontend/E2E/a11y | **Not Run** تا نصب وابستگی‌های npm/Playwright browsers |
| Architecture (AST) | قابل‌اجرا |

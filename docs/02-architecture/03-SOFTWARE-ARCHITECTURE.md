<div dir="rtl">

# سند ۳ — Software Architecture

| فیلد | مقدار |
|---|---|
| Document ID | DOC-03 |
| Version | 0.1 |
| Status | Draft — Complete برای MVP |
| Created / Updated | 2026-11-07 |
| Owner | Software Architect |
| Related Documents | DOC-01، DOC-05، DOC-06، DOC-07، DOC-08، DOC-09، DOC-15، DOC-17، ADR-0001..0007 |
| Related Decisions | DEC-001، 004، 006، 007، 123، 125، 129، 130 |

## 1. اصول
1. Modular Monolith (ADR-0001): یک Django project، ماژول‌های مستقل با Interface عمومی.
2. Safety Core پکیج پایتون خالص (بدون Django/LLM/HTTP) و تنها مرجع تصمیم ایمنی (ADR-0002).
3. منطق کسب‌وکار در لایه `services/` و `domain/`؛ View/Serializer فقط ورودی/خروجی.
4. وابستگی‌های خارجی (AI، پرداخت، پیام، ذخیره‌سازی، غذا) پشت Interface (DEC-007).
5. داده سلامت: حداقل، رمزنگاری‌شده در حالت ذخیره، رضایت‌محور، بدون ارسال خارجی (EXP-012).
6. هر خروجی برنامه/توصیه = `SafetyDecision` معتبر.

## 2. نمای کلی
```
Browser (Next.js PWA, RTL/LTR, Jalali/Gregorian)
   │ HTTPS  /api/v1  (cookie session + CSRF)
   ▼
Django (Modular Monolith) ── DRF API layer
   ├─ identity   ├─ profiles   ├─ onboarding  ├─ health
   ├─ safety (adapter) ──► safety_core (pure Python package)
   ├─ exercises  ├─ workout_engine ──► safety (port)  ├─ workout_logs
   ├─ nutrition (infra only)  ├─ ai_gateway ──► LLMProvider (port)
   ├─ subscriptions ──► PaymentProvider (port)  ├─ notifications ──► NotificationChannel (port)
   ├─ analytics  ├─ admin_panel  └─ compliance (consents, audit, export, deletion)
   ▼                    ▼                  ▼
PostgreSQL (+pgvector)   Redis (cache/rate limit/broker)   Object storage (port)
                        Celery workers (+ Outbox)
```

## 3. ماژول‌ها (شناسه، مسئولیت، مالک داده)
| MOD | App | مسئولیت | جداول مالک | وابستگی مجاز |
|---|---|---|---|---|
| MOD-IAM | `identity` | ثبت‌نام، ورود، نشست، نقش‌ها، رویداد احراز | users، user_sessions، authentication_events، user_roles | compliance (audit) |
| MOD-PRO | `profiles` | پروفایل، ترجیحات، تنظیمات i18n | user_profiles، user_preferences | identity |
| MOD-ONB | `onboarding` | ارزیابی مرحله‌ای، اهداف | assessments، assessment_answers، user_goals، equipment_inventory، availability_schedules | profiles، health |
| MOD-BODY | `body_metrics` | اندازه‌گیری‌ها | body_measurements | profiles |
| MOD-HEALTH | `health` | محدودیت/درد/علائم، وضعیت‌ها | health_conditions، symptom_records، pain_logs، medical_restrictions، professional_clearances | identity، compliance |
| MOD-SAFETY | `safety` | adapter: بارگذاری قواعد، ساخت SafetyRequest، ثبت تصمیم | safety_rule_versions، safety_rules، safety_decisions، red_flag_events | health، profiles، exercises (read port)، `safety_core` |
| — | `safety_core` | **پکیج خالص** منطق قواعد | — (stateless) | هیچ |
| MOD-EX | `exercises` | کاتالوگ حرکات، برچسب‌ها، گردش انتشار | exercises و جداول فرعی | compliance |
| MOD-WO | `workout_engine` | تولید/نسخه‌بندی برنامه | workout_plans، versions، phases، days، exercises، sets، plan_change_events | safety (port)، exercises، onboarding، profiles |
| MOD-LOG | `workout_logs` | جلسه و ثبت عملکرد | workout_sessions، exercise_logs، personal_records | workout_engine، health (علائم حین جلسه) |
| MOD-NUT | `nutrition` | زیرساخت (مدل خالی/Flag) — Phase 3 | foods…(Deferred) | safety |
| MOD-AI | `ai_gateway` | Provider abstraction، Prompt، Validator، سقف مصرف | ai_conversations، ai_messages، prompt_versions، ai_model_versions، ai_usage | safety (Validator port) |
| MOD-SUB | `subscriptions` | پلن، entitlement، سهمیه | features، subscription_plans، plan_features، plan_quotas، subscriptions | identity |
| MOD-NTF | `notifications` | اعلان/ایمیل از طریق Channel | notifications | identity |
| MOD-ANL | `analytics` | آمار پایه (خواندنی، مشتق) | views/materialized | logs، plans |
| MOD-ADM | `admin_panel` | پنل مدیریت، RBAC | — | همه (خواندن با مجوز) |
| MOD-AUD | `compliance` | رضایت، ممیزی، export، حذف، retention | user_consents، consent_documents، audit_logs، data_requests | — |
| MOD-I18N | `localization` | ترجمه محتوا، کتابخانه تاریخ | translations | — |

## 4. قوانین وابستگی (اجباری، CI با import-linter)
1. `safety_core` هیچ import از Django، DRF، `requests`، یا ماژول دیگر ندارد.
2. `workout_engine` و `ai_gateway` حرکت/توصیه را فقط از طریق `safety.ports.SafetyGate` تأیید می‌کنند.
3. ماژول‌ها به مدل‌های ماژول دیگر مستقیم دسترسی نمی‌دهند؛ فقط از `<app>.api` (service interface).
4. جهت وابستگی: `api(view) → services → domain ← repositories(models)`؛ domain به Django وابسته نیست (قدم‌به‌قدم؛ مدل‌های Django در `models.py`).
5. حلقه وابستگی ممنوع (import-linter contract `independence` + `layers`).
6. ارتباط ناهمگام بین ماژول‌ها: Outbox + Celery (رویداد: `plan_generated`، `session_finished`، …).
7. تست معماری: هیچ مسیر برگرداندن `Plan` به API بدون `decision_id` (AC-SAF-001).

## 5. ساختار Repository
```
/
├── backend/
│   ├── manage.py
│   ├── config/ (settings/base.py, dev.py, prod.py, urls.py, celery.py)
│   ├── apps/<module>/ (models.py, services/, domain/, api/ (views, serializers, urls), permissions.py, tests/)
│   ├── safety_core/ (models.py, engine.py, rules.py, errors.py, tests/)   # pure Python
│   ├── contracts/ (openapi.yaml → copy of DOC-07)
│   └── tests/ (architecture/, integration/, e2e-api/)
├── frontend/ (Next.js app router; i18n; design system)
├── shared/ (contracts: OpenAPI-generated types)
├── docs/
├── infra/ (docker/, compose files, ci/)
├── .env.example  README.md  CHANGELOG.md
```
> محدودیت محیط (ADR-0007): در این محیط Django/DRF قابل نصب نیست؛ `safety_core` به‌عنوان پکیج مستقل و کاملاً تست‌پذیر ابتدا ساخته می‌شود. بخش‌های Django با دقت نوشته می‌شوند اما تا زمان وجود Django در محیط وضعیت `Not Run` دارند.

## 6. جریان داده کلیدی: تولید برنامه
```
Client POST /workouts/generate
 → WorkoutService.generate(user)
   1. Preconditions: consent_health_valid? age≥18? (identity/compliance)
   2. SafetyRequest = SafetyAdapter.build(user)  (health, profile, flags)
   3. Candidate selection: ExerciseRepository.published() ∩ equipment ∩ level (deterministic)
   4. SafetyGate.evaluate(SafetyRequest, candidates) → SafetyDecision
        - STOP_AND_REFER / BLOCK_* / NEEDS_INFO → return Decision payload (no plan)
        - ALLOW/ALLOW_WITH_MODIFICATION → allowed set + per_item reasons
   5. PlanBuilder (rule-based; DOC-11) over allowed set
   6. SafetyGate.validate_plan(plan) (second pass; defense in depth)
   7. Persist plan_version + safety_decision_id; audit
 → Response: plan + rationale + confidence + decision_id
```
خطا در هر مرحله ← `ERROR_FAILSAFE` ← بدون برنامه.

## 7. AI Gateway (خلاصه؛ جزئیات DOC-08)
Request → Intent → Context (با Redaction) → Safety pre-check → (Retrieval) → `LLMProvider.generate` (Structured Output) → Validator (schema + Safety + منبع) → پاسخ. در MVP LLM فقط برای توضیح/خلاصه (اختیاری، پشت flag)؛ برنامه‌سازی کاملاً قاعده‌محور. `external_health_data=false` ثابت.

## 8. نقش‌ها و مجوزها
نقش‌ها: `user`، `professional` (Deferred)، `support_admin`، `content_admin`، `exercise_reviewer`، `nutrition_reviewer`، `clinical_safety_reviewer`، `finance_admin`، `super_admin`. مجوز دو سطحی: Role-based (API) + Object-level (مالکیت رکورد). ادمین فنی بدون `health_data_access` grant نمی‌تواند داده سلامت را ببیند؛ grant زمان‌دار و ممیزی‌شده.

## 9. Cache، Queue، Rate Limit
- Redis: cache کاتالوگ حرکات (غیرحساس)، rate limit (ورود/ثبت‌نام/AI)، broker Celery.
- هرگز داده سلامت در Redis بدون TTL کوتاه و کلید کاربر.
- Celery: ایمیل/اعلان، گزارش، export داده، حذف سخت (retention)، همگام‌سازی embedding (Phase 4).
- Outbox: جدول `outbox_events` در تراکنش دامنه؛ worker منتشر می‌کند (at-least-once، handlers idempotent).

## 10. Interfaces (Ports)
`LLMProvider`، `PaymentProvider`، `NotificationChannel`، `ObjectStorage`، `FoodDataSource`، `VectorStore`، `Clock`، `SafetyGate`. هر Port با Adapter آزمایشی (Fake) برای تست؛ Fake در Production ممنوع (بررسی config در startup).

## 11. i18n و تقویم
ترجمه رابط در فایل‌های JSON (Frontend) و جدول `translations` برای محتوا (حرکات). تاریخ: ذخیره UTC؛ نمایش با کتابخانه تاریخ (شمسی/میلادی) در Frontend؛ Backend ISO-8601. ارقام فارسی/لاتین از ترجیح. RTL/LTR با `dir` و `logical CSS properties.`

## 12. امنیت (خلاصه؛ DOC-15)
`Session cookie HttpOnly/Secure/SameSite`=Lax + CSRF؛ Argon2؛ rate limit؛ Validation سمت سرور (DRF serializers با فهرست سفید فیلد)؛ رمزنگاری فیلدهای حساس (فیلد رمزشده در سطح اپلیکیشن، کلیدها از Secret Manager/ENV)؛ لاگ بدون PII سلامت؛ dependency scan؛ headers (CSP، HSTS).

## 13. مشاهده‌پذیری
Structured logging (JSON) با `request_id`؛ Health endpoints `/health/live`، `/health/ready`؛ متریک‌ها؛ Error tracking (Provider-agnostic).

## 14. استقرار
Docker multi-stage؛ Compose: `backend`، `worker`، `frontend`، `postgres(pgvector)`، `redis`؛ پیکربندی از ENV؛ CI: lint، type-check، تست، import-linter، migration check، SCA. جزئیات DOC-17.

## 15. نگاشت قرارداد شناسه‌ها
MOD-* ماژول، ENT-* موجودیت (DOC-05)، API-* مسیر (DOC-07)، TST-* تست (DOC-16)؛ زنجیره ردیابی: Requirement → US → UI(PG-*) → API → ENT → Logic(SVC-*) → TST در DOC-19.

## 16. معیارهای پذیرش معماری
| ID | معیار |
|---|---|
| AC-ARCH-001 | import-linter: safety_core بدون وابستگی خارجی |
| AC-ARCH-002 | هیچ حلقه وابستگی بین ماژول‌ها |
| AC-ARCH-003 | همه Portها Fake و Real جدا دارند؛ Fake در prod رد می‌شود |
| AC-ARCH-004 | همه endpointها OpenAPI دارند و permission صریح |
| AC-ARCH-005 | هر مسیر ارائه برنامه SafetyDecision دارد |

</div>

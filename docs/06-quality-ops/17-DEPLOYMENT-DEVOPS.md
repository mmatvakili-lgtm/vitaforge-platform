<div dir="rtl">

# سند ۱۷ — Deployment & DevOps Specification

| فیلد | مقدار |
|---|---|
| Document ID | DOC-17 |
| Version | 0.1 |
| Status | Draft — Complete (طراحی)؛ **Not Run** (Docker/CI در این محیط اجرا نشده) |
| Created / Updated | 2026-11-07 |
| Owner | DevOps / Architect |
| Related Documents | DOC-03، DOC-15 |
| Related Decisions | DEC-006، 113؛ ADR-0006، ADR-0007 |

## 1. محیط‌ها
| محیط | هدف | داده | نکات |
|---|---|---|---|
| local/dev | توسعه | seed نمونه + حساب آزمایشی (`DEV_SEED=1`) | Compose |
| ci | تست | موقت | سرویس‌های Postgres/Redis |
| staging | پیش‌انتشار | بدون داده کاربر واقعی | آینه prod؛ محتوای Draft با برچسب |
| production | | داده واقعی | Fake providers/seed نمونه/`DEBUG` ممنوع (بررسی startup) |

## 2. اجزا (Compose)
`backend` (gunicorn)، `worker` (celery)، `beat`، `frontend` (Next.js)، `postgres` (pgvector image در Phase 4)، `redis`، `reverse-proxy` (TLS). ذخیره‌سازی شیء: Port (MinIO محلی/Provider بازار).

## 3. پیکربندی
12-factor: همه تنظیمات از ENV؛ `.env.example` با مقادیر ساختگی؛ Secret ها از `Secret Manager/Docker secrets`؛ `settings/{base,dev,prod}.py`؛ validation پیکربندی در startup (رد اجرای prod با Fake provider، `DEBUG=True`، کلید پیش‌فرض، `external_health_data=true` بدون ADR).

## 4. CI/CD (طراحی)
Pipeline: lint (ruff/eslint) → type (mypy/tsc) → unit → architecture (import-linter) → integration (Compose) → API contract → security (pip-audit, npm audit, bandit, secret scan) → build images → e2e (Playwright) → migration check → (CD) deploy staging → smoke → manual gate → prod.
Rollback: انتشار تصویر نسخه قبل + migration برگشت‌پذیر (طراحی دو مرحله‌ای: expand→migrate→contract)؛ هرگز migration مخرب در همان انتشار.

## 5. Migration
`makemigrations --check` در CI؛ هر migration داده‌ای idempotent؛ بازبینی SQL؛ بکاپ قبل از اعمال prod.

## 6. Backup/DR
RPO ≤ ۲۴ساعت، RTO ≤ ۸ساعت (فرض DEC-113)؛ pg_dump/WAL رمزنگاری‌شده؛ تست بازیابی فصلی؛ عدم بکاپ کلیدهای رمزنگاری کنار داده.

## 7. مشاهده‌پذیری
Logging ساختاریافته JSON (`request_id`)، بدون PHI؛ `/health/live` و `/health/ready`؛ متریک (درخواست، تأخیر، خطا، صف Celery، نرخ STOP/BLOCK Safety)؛ Error tracking با scrubbing؛ هشدار روی `ERROR_FAILSAFE` غیرمنتظره.

## 8. امنیت استقرار
کاربر غیر root در کانتینر؛ تصویر حداقلی؛ اسکن تصویر؛ شبکه داخلی بین سرویس‌ها؛ فقط proxy عمومی؛ headers/CSP در proxy.

## 9. قابلیت تعویض بازار (DEC-006)
هیچ وابستگی به ابر خاص؛ Providerها از ENV (`PAYMENT_PROVIDER`، `LLM_PROVIDER`، `NOTIFY_PROVIDER`، `STORAGE_PROVIDER`).

## 10. معیارهای پذیرش
| ID | معیار |
|---|---|
| AC-OPS-001 | `docker compose up` از صفر سرویس‌ها را بالا می‌آورد و `/health/ready` سبز (Not Run تا اجرا) |
| AC-OPS-002 | استارت prod با پیکربندی ناامن رد می‌شود (تست واحد قابل‌اجرا) |
| AC-OPS-003 | migration up/down در CI |
| AC-OPS-004 | بکاپ/بازیابی مستند و تمرین‌شده (Pending) |

</div>

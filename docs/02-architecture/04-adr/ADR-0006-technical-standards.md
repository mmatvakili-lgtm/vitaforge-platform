<div dir="rtl">

# ADR-0006 — استانداردهای فنی مستقل (گروه A)

| فیلد | مقدار |
|---|---|
| Status | Accepted |
| Date | 2026-11-07 |
| Owner | Architect |
| Related Decisions | DEC-130 |
| Related Documents | DOC-03، DOC-20 |

| موضوع | انتخاب | دلیل |
|---|---|---|
| State در Frontend | TanStack Query (server state) + Zustand (UI state) | سادگی، کمترین boilerplate |
| Cache | Redis؛ کش فقط داده غیرحساس یا کلید به‌ازای کاربر با TTL | کارایی + حریم |
| Queue | Celery + الگوی Outbox برای رویدادهای تراکنشی | اطمینان تحویل |
| Versioning API | `/api/v1` + OpenAPI؛ تغییر شکننده = نسخه جدید | قابلیت نگهداری |
| Versioning محتوا/قواعد | immutable؛ تغییر = نسخه جدید؛ `rule_set_version` | ممیزی ایمنی |
| تست | pytest، Playwright، import-linter، تست معماری | تست‌پذیری |
| کیفیت کد | ruff، mypy، eslint، prettier، pre-commit | یکنواختی |
| شناسه‌ها | UUID؛ زمان UTC | سند مادر §27 |
**قابل‌بازگشت:** بله، با ADR جدید.

</div>

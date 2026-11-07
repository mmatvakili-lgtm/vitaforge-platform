<div dir="rtl">

# ADR-0007 — محدودیت محیط اجرا و ترتیب پیاده‌سازی

| فیلد | مقدار |
|---|---|
| Status | Accepted |
| Date | 2026-11-07 |
| Owner | Architect |
| Related Decisions | DEC-130 |

**مسئله:** در محیط فعلی شبکه بسته است (pip/npm نصب نمی‌شوند)، Django/DRF نصب نیست؛ Python 3.13، Node 22، pytest، psql و redis-server موجودند.
**گزینه‌ها:** (A) توقف کدنویسی؛ (B) ساخت `safety_core` به‌صورت پکیج خالص پایتون و Workout Engine دامنه‌ای (بدون Django) با تست کامل، و نوشتن لایه Django/Next.js با وضعیت `Not Run`.
**انتخاب:** B.
**پیامد:** Milestone 4 (Safety Core) پیش از Identity اجرا و کاملاً تست می‌شود؛ کد Django/DRF/Next.js بدون اجرا «Written, Not Run» گزارش می‌شود و به‌عنوان قابلیت تکمیل‌شده اعلام نمی‌شود. تغییر محیط (دسترسی شبکه) ← اجرای تست‌های Django.

</div>

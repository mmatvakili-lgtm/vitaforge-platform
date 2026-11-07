<div dir="rtl">

# ADR-0003 — Feature Gating با پرچم safety_critical (حل CON-004)

| فیلد | مقدار |
|---|---|
| Status | Accepted |
| Date | 2026-11-07 |
| Owner | Architect |
| Related Decisions | DEC-005، DEC-110، DEC-126 |
| Related Documents | DOC-03، DOC-20 |

**مسئله:** ایمنی نباید پولی شود؛ پلن Free تعریف نشده بود.
**انتخاب:** جدول `features` با `safety_critical`؛ دسترسی = `entitlement ∧ quota` و برای `safety_critical` همیشه مجاز. پلن Free طبق PRD §5.13.1.
**پیامد:** تست معماری: هیچ Gate پولی روی feature با `safety_critical=true` وجود ندارد؛ پایان اشتراک ← Free بدون از دست رفتن داده.
**گزینه ردشده:** قفل‌کردن ثبت محدودیت/هشدار برای تشویق به خرید (ممنوع).

</div>

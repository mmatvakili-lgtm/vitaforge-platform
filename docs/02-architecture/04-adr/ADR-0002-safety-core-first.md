# ADR-0002 — Safety Core پایه از Phase 1 (حل CON-001)

| فیلد | مقدار |
|---|---|
| Status | Accepted |
| Date | 2026-11-07 |
| Owner | Architect |
| Related Decisions | DEC-001، CON-001 |
| Related Documents | DOC-03، DOC-20 |

**مسئله:** سند مادر می‌گوید همه حرکات از Safety Engine بگذرند، اما Roadmap آن را به Phase 2 برده بود.
**گزینه‌ها:** (A) تأخیر Safety به Phase 2؛ (B) Safety Core پایه در Phase 1 و Engine کامل مرحله‌ای.
**انتخاب:** B.
**تصمیم:** Phase 1 شامل: SafetyRequest/Decision، قواعد ساختاری SAF-R001..R012، غربالگری هشدار (محتوا Draft)، فیلتر سخت، Fail-safe، ثبت `safety_decisions`. Safety Core پکیج دامنه‌ای بدون وابستگی به DRF/LLM. تنها مسیر نمایش برنامه: `decision_id` معتبر (تست معماری AC-SAF-001).
**پیامد:** Roadmap (DOC-18) و Workout Engine باید Safety Core را وابستگی Phase 1 بدانند؛ Phase 2 تکمیل مسیرها، پایش، جایگزین‌ها.
**ریسک:** محتوای بالینی بدون تأیید → حالت محافظه‌کارانه (DOC-09 §8).

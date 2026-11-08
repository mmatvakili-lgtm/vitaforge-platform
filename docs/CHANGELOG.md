<div dir="rtl">

# CHANGELOG

## 2026-11-09
- اعتبارسنجی واقعی قرارداد OpenAPI روی `devserver` برای ۵۶ عملیات (`backend/contract`، ۹۸ تست)؛ `CONTRACT_REPORT.md`؛ spec به 3.1.0 و افزودن 400 (DEC-146/147).
- بانک حرکات: `license_status`، `limitations`، `review_notes`، واژگان کنترل‌شده، مانع انتشار؛ ۵ حرکت کششی وزن بدن (Experimental/Pending Review) (DEC-149).
- DEC-146..149، OPEN-009..012.

## 2026-11-08
- `MVP_GAP_ANALYSIS.md`: ارزیابی واقعی فاصله تا MVP (سطح ماژول‌ها، Mock/Stub، شکاف داده، مجوز منابع، معیار تکمیل). بدون تغییر کد.

## 2026-11-07
- Batch 1: 00-INDEX، 01-PRD v0.2، 09-Safety v0.2، 20-Decisions v0.2، OPEN_DECISIONS، ADR-0001..0006.
- Batch 2: 02-USER-STORIES، 03-SOFTWARE-ARCHITECTURE، 04-ADR-REGISTER (+ADR-0007)، 05-DATABASE-ERD (۶۷ موجودیت، Mermaid تأییدشده با mmdc)، 06-DATA-DICTIONARY (تولید از منبع واحد).
- Batch 3: 07-OPENAPI (۵۶ endpoint، ۶۸ schema، ارجاع‌ها معتبر)، 08-AI، 10-Exercise DB، 11-Workout Engine، 12-Nutrition (Deferred)، 13-Design System (تضاد رنگ‌ها محاسبه‌شده)، 14-UI، 15-Security، 16-Testing، 17-DevOps، 18-Roadmap، 19-Traceability (۱۱۲ FR، ۵۱ US، بدون FR بدون پوشش P0/P1)، MVP_SCOPE، IMPLEMENTATION_PLAN.

## 2026-11-07 (۲)
- مخزن GitHub راه‌اندازی شد؛ سیاست زبان + `lint_docs`/`normalize_docs`.
- `safety_core`: engine، validate_plan، find_alternatives + ۷۲ تست.
- `ai_gateway`، `entitlements`، `app_services` (identity، health_profile، workouts)، `devserver` (WSGI + UI آزمایشی)؛ ۱۶۹ تست سبز.
- ترجیح حرکات حمایتی (`supports_regions`) برای سابقه بدون درد، پشت فیلتر ایمنی؛ `OPEN-008`.
- اندازه‌گیری بدن، ثبت درد، داشبورد، پیشرفت ماهانه، خروجی و حذف داده؛ ۱۹۷ تست.
- پیاده‌سازی همه ۵۶ endpoint در آداپتور توسعه (بازیابی گذرواژه، پروفایل، علائم، نسخه‌های برنامه، ادمین، گفتگوی AI با Provider پیکربندی‌نشده → fallback)؛ ۲۰۲ تست.
- `exercise_catalog` (schema، importer، منابع، ۲۵ حرکت نمونه)، `nutrition_engine`، `progression`/recovery، لایه تصمیم AI، توضیح ایمنی؛ `DECISION_REGISTRY` و `CAPABILITY_STATUS`؛ ۲۸۰ تست.

</div>

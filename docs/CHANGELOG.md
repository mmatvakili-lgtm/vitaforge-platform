<div dir="rtl">

# CHANGELOG

## 2026-11-15
- عملکرد: بارگذاری کاتالوگ فقط یک‌بار در هر فرایند و حذف اسکن کامل کاتالوگ در هر درخواست؛ کش ۳ثانیه‌ای درخواست‌های GET یکسان در مرورگر (حذف درخواست‌های تکراری هدر/داشبورد)؛ اسکریپت `npm run local` برای اجرای سریع (build + start) به‌جای حالت dev.
- پوسته‌ی موبایل‌فرست: دوک شیشه‌ای شناور پایین، پنل «بیشتر» به‌صورت sheet، نوار بالای باریک با خط پیشرفت اسکرول، اسکرول‌بار طراحی‌شده، پس‌زمینه‌ی aurora، کارت/دکمه/نوار پیشرفت زنده.
- انیمیشن حرکت‌ها اکنون روی مانکن سه‌بعدی اسکین‌شده (CC0) اجرا می‌شود: IK خودی برای همه‌ی حرکت‌ها و کلیپ‌های واقعی موشن‌کپچر CC0 برای شنا، جامپینگ‌جک، دویدن و راه‌رفتن؛ در نبود WebGL به اسکلت دوبعدی برمی‌گردد.
- انیمیشن اجرای حرکت برای هر ۲۲۹ حرکت (اسکلت دوبعدی با IK، ۵۸ الگوی حرکتی، هایلایت عضله‌ی هدف) در صفحه‌ی برنامه، تمرین و جزئیات حرکت؛ ساخته‌ی خود پروژه، بدون منبع خارجی (مجوز تصاویر free-exercise-db مشخص نیست).
- رفع بن‌بست «برنامه ساخته نمی‌شود» روی اجرای محلی: با `DJANGO_DEBUG=true` محتوای نمونه (برچسب آزمایشی + هشدار) به‌صورت پیش‌فرض فعال است؛ حالت سخت‌گیرانه با `VITAFORGE_DEV_CONTENT=false`.
- موتور تمرین آگاه از ارزیابی حرکتی (سختی هدف، ست اضافه برای الگوی ضعیف، حرکت اصلاحی، ترجیح تک‌طرفه)؛ ایمنی همچنان تنها تأییدکننده (PR #23).
- تحلیل تمرین `API-ANALYTICS-001` و صفحه‌ی تحلیل (PR #24).
- پیکربندی استقرار رایگان `render.yaml` و `DEPLOY_FREE.md` (PR #25).
- UI نسل ۲: سه پوسته، تایپوگرافی، بدن سه‌بعدی رویه‌ای (PR #26)؛ بانک حرکات دسته‌ی ۴ (۲۲۹ حرکت) و بدن در داشبورد (PR #27)؛ بدن هدف هر روز در برنامه (PR #28).
- بازطراحی جریان کاربر: هدر آگاه از ورود (نوار تب پایین موبایل + منوی «بیشتر»)، صفحه‌ی «امروز» با مسیر راهنما و «گام بعدی» (آشناسازی ← ارزیابی ← برنامه ← تمرین ← مرور)، کارت تمرین امروز با بدن هدف (`lib/journey.ts`).
- دوره‌بندی هفتگی (موج ۴ هفته‌ای: پایه/ساخت/اوج/دیلود) و دیلود خودکار با سیگنال RPE بالا یا بازگشت پس از وقفه؛ فقط کاهش می‌دهد، هرگز افزایش نمی‌دهد؛ دلیل‌ها در `rationale.reasons` و نمایش در صفحه‌ی برنامه (`workout_engine/periodization.py`).
- موتور برنامه بدون بن‌بست: در ماتریس ۸۶۴ ترکیب هدف/سطح/روز/تجهیزات/زمان، ۲۲۱ مورد NEEDS_CONTENT می‌داد و اکنون صفر؛ روزها چندعضله‌ای و چرخشی (`Full Body A/B/C`، Upper/Lower A/B، Push/Pull/Legs با پوشش متقاطع)؛ جایگزینی الگو، تطبیق ست/استراحت با زمان، بازگشت به ساختار دیگر (DEC-160؛ `e2e/test_plan_balance.py`).

## 2026-11-09 (ب)
- `Django Runtime Validation`: **Not Run** (بدون شبکه؛ لایه Django ۵۶ عملیات ندارد) — `DJANGO_RUNTIME_VALIDATION.md`، `tools/django_preflight.py`.
- امنیت انتشار حرکات: بستن مسیرهای دور زدن (سرویس، Bridge، Loader، CheckConstraint)؛ `EXERCISE_CATALOG_SECURITY.md`؛ `API_GAPS.md`.
- DEC-150/151، OPEN-013.

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

<div dir="rtl">

- تب «عکس مرجع» در کارت انیمیشن حرکت: ۸۳ حرکت با دو عکس شروع/پایان (free-exercise-db) در کنار مانکن سه‌بعدی؛ کش SW؛ اعتبار و ریسک مجوز در THIRD_PARTY_LICENSES.

</div>

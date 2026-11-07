# سند ۱۰ — Exercise Database Specification

| فیلد | مقدار |
|---|---|
| Document ID | DOC-10 |
| Version | 0.1 |
| Status | Draft — ساختار Complete؛ **محتوای حرکات: Pending Specialist Approval (EXP-003)** |
| Created / Updated | 2026-11-07 |
| Owner | Exercise Content Lead |
| Related Documents | DOC-05، DOC-06، DOC-09، DOC-11، DOC-14 |
| Related Decisions | DEC-107، 108؛ ASM-003؛ EXP-003 |

## 1. هدف
کاتالوگ حرکات ساختاریافته که Safety Core بتواند سازگاری را **قطعی** از روی برچسب‌ها محاسبه کند. هیچ حرکتی بدون برچسب ایمنی کامل و بازبینی منتشر نمی‌شود (SAF-R005).

## 2. ساختار رکورد (ارجاع DOC-06)
`exercises` + `exercise_translations` (fa/en) + `exercise_muscles` + `exercise_equipment` + `exercise_region_loads` + `exercise_cautions` + `exercise_contraindications` + `exercise_alternatives` + `exercise_media` + `exercise_sources` + `exercise_review_events`.

### 2.1 فیلدهای الزامی برای انتشار (Publish gate)
| گروه | الزام |
|---|---|
| هویت | `stable_code` یکتا، نام fa و en، مترادف‌ها |
| عضلات | حداقل ۱ primary |
| الگو | `movement_pattern` از فهرست سند مادر (Squat، Hinge، Lunge، Push، Pull، Carry، Rotation، Anti-Rotation، Locomotion، Jump/Land، Cardio) |
| تجهیزات | حداقل یک ردیف (یا «وزن بدن») |
| دشواری/مهارت | `difficulty`، `skill_level` |
| اجرا | setup، `execution_steps`، breathing، `common_mistakes`، tempo پیش‌فرض |
| ایمنی | `exercise_region_loads` برای **همه ۱۵ ناحیه** (مقدار صریح `none/low/moderate/high`، نه خالی)؛ cautions/contraindications (می‌تواند خالی ولی «بازبینی‌شده: بدون مورد» ثبت شود) |
| روابط | حداقل یکی از alternative/regression/progression یا نشانه صریح «بدون جایگزین» |
| منبع | حداقل یک `exercise_sources` یا `evidence_level=none` صریح |
| رسانه | اختیاری؛ در صورت وجود `license_status=licensed` |
| گردش | رد شدن از Scientific Review و Safety Review (دو بازبین متفاوت) |

`safety_tags_complete` توسط سرویس به‌صورت **محاسبه‌شده** تنظیم می‌شود (نه ویرایش دستی) و CHECK دیتابیس انتشار بدون آن را رد می‌کند.

## 3. گردش انتشار
```
draft → scientific_review → safety_review → published → (retired)
   ▲________________ بازگشت با دلیل ___________________|
```
- نقش‌ها: `content_admin` (draft)، `exercise_reviewer` (scientific)، `clinical_safety_reviewer` (safety)، انتشار فقط پس از safety_review.
- هر تغییر محتوایی روی `published` ← نسخه جدید (version+1) و بازگشت به draft برای نسخه جدید؛ نسخه فعلی تا انتشار نسخه جدید فعال می‌ماند.
- `exercise_review_events` همه گذارها را ثبت می‌کند.

## 4. برچسب‌های ایمنی و استفاده توسط Safety Core
| برچسب | استفاده |
|---|---|
| `region_loads[region]` | قاعده: ناحیه دارای محدودیت فعال + loading ≥ آستانه ← BLOCK (آستانه به‌ازای نوع محدودیت از `medical_restrictions.max_loading`؛ مقدار پیش‌فرض بالینی **تعریف نشده** → محافظه‌کارانه: هر loading ≠ none در ناحیه درگیر مسدود) |
| `contraindications` | تطبیق با وضعیت/ناحیه ← BLOCK |
| `cautions` | ← ALLOW_WITH_MODIFICATION یا `caution` در UI |
| `movement_pattern` | محدودیت الگو (`medical_restrictions.restricted_pattern_id`) |
| `difficulty/skill_level` | انتخاب Workout Engine |
| `review_status`/`version` | فقط published |

## 5. محتوای اولیه (Seed)
- **ساختار Seed:** فایل‌های YAML در `backend/seed/exercises/*.yaml` با اعتبارسنج.
- **محتوای واقعی حرکات:** نوشته‌شدنی توسط تیم محتوا/متخصص؛ این پروژه **داده نمونه آزمایشی** تولید می‌کند که `review_status=draft` و `evidence_level=none` دارد، با برچسب `SAMPLE_UNREVIEWED`؛ در Production seed نمونه بارگذاری نمی‌شود (بررسی startup).
- تعداد هدف MVP: ۱۵۰–۳۰۰ (ASM-003).

## 6. پوشش مورد انتظار (ماتریس پوشش)
برای هر ترکیب (هدف × تجهیزات: باشگاه/خانه/بدون تجهیزات × الگوی حرکتی) حداقل N حرکت published لازم است تا Workout Engine بتواند برنامه بسازد؛ در غیر این صورت `NEEDS_CONTENT` (برنامه ساخته نمی‌شود و پیام «محتوا ناکافی»). گزارش پوشش در پنل ادمین.

## 7. رسانه و حقوق
`exercise_media.license_status` ∈ {licensed, pending, rejected}؛ فقط licensed به کاربر نمایش داده می‌شود؛ بدون رسانه ← برچسب «بدون رسانه» (DEC-107). ذخیره از طریق `ObjectStorage` Port؛ آپلود امن (اندازه/نوع/اسکن).

## 8. جست‌وجو
trigram + GIN روی نام و مترادف (fa/en)، نرمال‌سازی فارسی (ی/ک عربی، ZWNJ، اعداد)؛ فیلترها: عضله، تجهیزات، سطح، الگو.

## 9. ترجمه
متن fa/en هر دو الزامی برای انتشار؛ ترجمه بازبینی‌شده؛ نام انگلیسی کنار نام فارسی نمایش داده می‌شود.

## 10. معیارهای پذیرش
| ID | معیار |
|---|---|
| AC-EX-001 | انتشار بدون ۱۵ ناحیه region_load رد شود |
| AC-EX-002 | انتشار بدون دو بازبینی رد شود |
| AC-EX-003 | حرکت retired/draft هرگز در API کاربر نیاید |
| AC-EX-004 | رسانه unlicensed نمایش داده نشود |
| AC-EX-005 | Seed نمونه در prod بارگذاری نشود |

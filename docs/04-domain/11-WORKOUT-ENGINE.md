<div dir="rtl">

# سند ۱۱ — `Workout Engine Specification`

| فیلد | مقدار |
|---|---|
| Document ID | DOC-11 |
| Version | 0.1 |
| Status | Draft — الگوریتم Complete؛ **پارامترهای تمرینی: Unverified — `Pending Specialist Approval` (Exercise Reviewer)** |
| Created / Updated | 2026-11-07 |
| Owner | Training Systems Lead |
| Related Documents | DOC-09، DOC-10، DOC-05، DOC-07 |
| Related Decisions | DEC-001، 108، 132؛ ADR-0002 |

> تمام اعداد جدول پارامترها **پیش‌فرض فنی قابل پیکربندی** هستند، نه توصیه بالینی/علمی تأییدشده. در Production باید توسط Exercise Reviewer بازبینی و در `engine_config` نسخه‌دار شوند (EXP-013). تا آن زمان UI برچسب «برنامه آزمایشی» نمایش می‌دهد و انتشار برای کاربر واقعی Blocked است.

## 1. اصول
1. قاعده‌محور و قطعی (بدون LLM)؛ خروجی قابل بازتولید با `inputs_hash`.
2. هر حرکت از Safety Core عبور می‌کند (دو بار: انتخاب نامزد و اعتبارسنجی نهایی).
3. در نبود حرکت مجاز/محتوای کافی: برنامه ساخته نمی‌شود (`NEEDS_CONTENT`) یا بخشی از برنامه حذف و اعلام می‌شود؛ حدس نمی‌زند.
4. دلیل انتخاب و سطح اطمینان همراه هر برنامه.
5. مسیرهای B و C: فقط طبق DOC-09 (B: بدون برنامه درمانی؛ C: Deferred).

## 2. ورودی‌ها
`EngineInput`: goal، level، days_available (روز و دقیقه)، equipment، preferred_structure، age، sex(اختیاری، فقط اگر لازم)، `SafetyDecision` + `allowed_exercises` (خروجی Safety Core)، تاریخچه پایبندی (اختیاری)، `engine_config` version.
پیش‌شرط‌ها: Onboarding کامل، رضایت سلامت معتبر، `SafetyDecision.status ∈ {ALLOW, ALLOW_WITH_MODIFICATION}`.

## 3. الگوریتم تولید برنامه (مراحل)
```
S0  validate input → در کمبود داده: NEEDS_INFO با پرسش‌ها (از Safety/Onboarding)
S1  Safety pre-pass: allowed = SafetyGate.filter(published ∩ equipment ∩ level_cap)
S2  Choose structure (جدول §4)
S3  Build day templates: slots (الگوی حرکتی/عضله/نقش) برای هر روز
S4  Fill slots: انتخاب قطعی از allowed با امتیاز (§5)؛ اگر slot خالی ← جایگزین ← در نبود: slot حذف + note
S5  Prescribe sets/reps/rest/RPE (جدول §6) متناسب با goal/level
S6  Check constraints (§7): حجم هفتگی، تنوع، تعادل push/pull، زمان جلسه
S7  Safety post-pass: SafetyGate.validate_plan(plan) ← تضمین نهایی (در شکست: ERROR_FAILSAFE)
S8  Persist plan_version (immutable) + safety_decision_id + rationale + confidence
```
Confidence: `high` اگر همه slotها با حرکت اولویت اول پر و محتوا کافی؛ `medium` اگر ≥۱ جایگزین؛ `low` اگر slotی حذف شده یا پوشش محتوا کم.

## 4. انتخاب ساختار (قابل تغییر؛ هرگز تحمیل نمی‌شود)
| روز در هفته | پیش‌فرض (config) | جایگزین‌های مجاز |
|---|---|---|
| ۱–۲ | Full Body | custom |
| ۳ | Full Body | Upper/Lower+FB hybrid |
| ۴ | Upper/Lower | PPL-hybrid |
| ۵–۶ | PPL یا Upper/Lower+ | hybrid |
اگر کاربر ساختار ترجیحی داد و با روزها سازگار بود، همان؛ در غیر این صورت دلیل در `rationale. Bro Split` فقط در حالت `custom` و با برچسب «غیرپیش‌فرض».

## 5. امتیازدهی حرکت برای Slot (قطعی)
`score = w1·pattern_match + w2·muscle_coverage + w3·equipment_pref + w4·difficulty_fit + w5·preference + w6·variety − w7·repeat_penalty − w8·caution_penalty`
- وزن‌ها در `engine_config`؛ تساوی با `stable_code` مرتب می‌شود (قطعیت).
- `caution_penalty` برای حرکات `ALLOW_WITH_MODIFICATION`.
- حرکات `blocked` اصلاً در allowed نیستند.

## 6. تجویز ست/تکرار/استراحت (پیش‌فرض‌های Unverified)
| Goal | Level | ست/حرکت | تکرار | RPE هدف | استراحت (ثانیه) |
|---|---|---|---|---|---|
| strength | beginner | 3 | 5–8 | 6–7 | 120–180 |
| strength | intermediate/advanced | 3–5 | 3–6 | 7–8 | 150–240 |
| muscle_gain | beginner | 2–3 | 8–12 | 6–7 | 60–90 |
| muscle_gain | intermediate/advanced | 3–4 | 6–12 | 7–9 | 60–120 |
| general_fitness | any | 2–3 | 10–15 | 5–7 | 45–75 |
| fat_loss | any | 2–3 | 10–15 | 6–8 | 45–75 |
| endurance/mobility/sport | — | **Deferred** (مدل رشته‌ای Phase 4–5) |
- RIR = 10 − RPE (نمایش جایگزین). Warm-up: نوع حرکت سبک‌شده/تحرک‌پذیری از catalog (`exercise_type=mobility`) یا بدون بار. Cooldown اختیاری.
- Tempo از `default_tempo`.

## 7. قیدها
| ID | قید |
|---|---|
| WO-C01 | زمان جلسه ≤ `session_minutes`: برآورد = Σ(ست × (زمان اجرا + استراحت)) + warmup؛ حذف از انتهای accessory تا جا شود |
| WO-C02 | تنوع: یک حرکت > `max_repeat_per_week` تکرار نشود |
| WO-C03 | تعادل: نسبت push:pull در بازه config؛ گروه عضلانی بدون پوشش اعلام شود |
| WO-C04 | حجم هفتگی هر گروه ≤ سقف level (config) |
| WO-C05 | شروع مبتدی: حرکات `difficulty ≤ beginner/skill ≤ cap` |
| WO-C06 | هیچ جلسه‌ای بدون حرکت main نباشد؛ در غیر این صورت NEEDS_CONTENT |

## 8. پیشرفت (Progression)
- روش‌ها: Double Progression (پیش‌فرض)، Linear Progression (مبتدی، حرکات اصلی)، Autoregulation با RPE. Periodization/Volume-Intensity: Deferred.
- **Double Progression:** اگر در همه ست‌ها به سقف تکرار برسد و RPE ≤ هدف ← افزایش بار به اندازه `load_step` (config، به‌ازای تجهیزات)، بازگشت تکرار به کف.
- قاعده **یک متغیر در هر بار** (SAF-R010): افزایش هم‌زمان بار و حجم در یک مرحله رد می‌شود.
- پیشنهاد پیشرفت فقط وقتی: ≥ ۲ جلسه سابقه همان حرکت؛ هیچ هشدار/درد فعال مرتبط؛ مسیر A یا سالم. **در مسیر B و C قفل**.
- **Deload:** تریگر: (الف) هر N هفته (config) یا (ب) افت عملکرد/RPE بالا در ≥ ۲ جلسه پیاپی. کاهش حجم/بار با ضریب config؛ پیشنهاد، نه اجبار؛ با دلیل.
- **جلسه از دست‌رفته:** جبران افراطی ممنوع؛ برنامه هفته بعد بدون انباشت.

## 9. جایگزینی حرکت
در جلسه/برنامه: الگوریتم DOC-09 §9 (نامزد: alternatives ∪ regressions → فیلتر Safety → امتیاز). ثبت علت (`pain|equipment|preference|other`)؛ علت `pain` ← ثبت `pain_log` + ارزیابی Safety مجدد (امکان STOP). نسخه جدید برنامه ایجاد می‌شود؛ `plan_change_events` ثبت.

## 10. نسخه‌بندی
`workout_plan_versions` تغییرناپذیر؛ هر تولید/جایگزینی/پیشرفت = نسخه جدید؛ بازگشت به نسخه قبل = نسخه جدید با محتوای قبلی (تاریخچه حفظ). `engine_config_version` و `rule_set_version` در rationale ثبت می‌شوند.

## 11. خروجی‌ها
`PlanResult`: plan (روزها/حرکات/ست)، `rationale` (ساختار، دلایل هر حرکت، قیدهای اعمال‌شده)، `confidence`، `omissions[]` (slotهای حذف‌شده با علت)، `safety_decision_id`.

## 12. معیارهای پذیرش
| ID | معیار |
|---|---|
| AC-WO-001 | بدون SafetyDecision معتبر هیچ برنامه‌ای ساخته نمی‌شود |
| AC-WO-002 | هر حرکت برنامه ∈ allowed و published |
| AC-WO-003 | خروجی برای ورودی یکسان بایت‌به‌بایت یکسان (قطعیت) |
| AC-WO-004 | زمان جلسه ≤ زمان کاربر |
| AC-WO-005 | افزایش دو متغیری رد می‌شود |
| AC-WO-006 | محتوای ناکافی ← NEEDS_CONTENT، نه برنامه ناقص بی‌اعلام |
| AC-WO-007 | بلوک‌های محدودیت ناحیه‌ای: حرکت منع‌شده هرگز ظاهر نشود (تست property-based) |

</div>

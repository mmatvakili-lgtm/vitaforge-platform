<div dir="rtl">

# سند ۱۴ — `Page-by-Page UI Specification`

| فیلد | مقدار |
|---|---|
| Document ID | DOC-14 |
| Version | 0.1 |
| Status | Draft — Complete برای صفحات MVP؛ صفحات Backlog: Deferred |
| Created / Updated | 2026-11-07 |
| Owner | UI/UX Designer |
| Related Documents | DOC-13، DOC-02، DOC-07 |
| Related Decisions | DEC-003، 004، 005، 125 |

قالب هر صفحه: **PG-id | مسیر | نقش/دسترسی | هدف | بخش‌ها | تعاملات | حالت‌ها (Loading/Empty/Error/Denied) | Responsive | API | US**.
همه صفحات: RTL/LTR، شمسی/میلادی، Light/Dark، a11y طبق DOC-13. حالت‌های سراسری (Loading=Skeleton، Error=ErrorState، Denied=AccessDenied) برای همه صفحات اعمال می‌شود و تکرار نمی‌شود مگر رفتار خاص.

## ۱. عمومی (Public)
| PG | مسیر | محتوا/رفتار | API | MVP |
|---|---|---|---|---|
| PG-PUB-001 Landing | `/` | Hero (ارزش پیشنهادی ایمنی‌محور)، چگونه کار می‌کند، دوزبانه؛ بدون ادعای درمان؛ CTA ثبت‌نام | — | ✔ |
| PG-PUB-002 Features/How/Pricing | `/pricing` و ... | جدول پلن‌ها از `GET /subscriptions/plans`؛ ردیف «ایمنی در همه پلن‌ها»؛ قیمت: «به‌زودی» تا DEC-104 | API-SUB-001 | ✔ |
| PG-PUB-003 FAQ/About/Legal-Privacy | `/faq` `/about` `/legal/*` | محتوای ایستا؛ متن حقوقی `Pending Legal Review` (برچسب Draft در staging) | — | ✔ (محتوا Draft) |
| PG-AUTH-001 Register | `/register` | ایمیل/موبایل، رمز (راهنمای قدرت)، تاریخ تولد (DatePicker)، زبان؛ خطای سن <۱۸ | API-AUTH-001 | ✔ |
| PG-AUTH-002 Verify | `/verify` | کد ۶ رقمی، ارسال مجدد با شمارنده | API-AUTH-002 | ✔ |
| PG-AUTH-003 Login | `/login` | شناسه+رمز؛ قفل/rate limit پیام | API-AUTH-003 | ✔ |
| PG-AUTH-004 Reset | `/reset` `/reset/confirm` | دو مرحله | API-AUTH-005/006 | ✔ |

## ۲. Onboarding
**PG-ONB-001 `/onboarding`** (کاربر ثبت‌نام‌شده؛ مسدود تا تکمیل برای صفحات برنامه)
- Stepper ۱۴ مرحله (سند مادر §5): زبان/کشور/واحد/تقویم → هدف → سن/اطلاعات پایه → اندازه‌ها (اختیاری) → سابقه/سطح → **رضایت + سلامت/درد/محدودیت + غربالگری هشدار** → تجهیزات → روزها/مدت → ترجیحات → تغذیه (Deferred: مرحله نمایش داده نمی‌شود/غیرفعال) → بودجه (Deferred) → خلاصه/تأیید → تولید برنامه.
- هر مرحله: دلیل جمع‌آوری (متن کمک)، ذخیره خودکار، «بعداً» برای اختیاری‌ها، ادامه پس از خروج.
- مرحله سلامت: ConsentGate (رضایت health_data) → فرم Conditions (ناحیه با نقشه‌بدن ساده + لیست قابل‌دسترس) → غربالگری (پرسش‌ها از API؛ محتوا Draft تا EXP) → نتیجه SafetyDecision (SafetyDecisionPanel).
- STOP/BLOCK: نمایش صفحه ایمنی؛ مسیر «ادامه بدون برنامه» (Dashboard با بنر) یا «ارجاع».
- آفلاین: بنر + غیرفعال‌کردن ارسال مراحل سلامت.
- API: API-ONB-001..003، API-HEALTH-002/006، API-PRIV-001/002. US: ONB-001/002، SAFE-001/004/005.
- Responsive: موبایل تک‌ستون با Sticky footer؛ دسکتاپ دوستونه (فرم + خلاصه).

## ۳. اپ (کاربر)
| PG | مسیر | هدف و بخش‌ها | تعاملات/حالت‌ها | API | US |
|---|---|---|---|---|---|
| PG-DASH-001 Dashboard | `/app` | «امروز»: جلسه امروز (CTA شروع)، برنامه جاری، خلاصه هفتگی، اهداف، هشدارهای ایمنی (بنر دائمی تا اقدام)، AI (اگر فعال) | Empty: بدون برنامه → CTA تولید؛ Denied: Onboarding ناقص → هدایت؛ Offline بنر | API-DASH-001 | DASH-001 |
| PG-PRO-001 Profile/Settings | `/app/settings` | زبان، تقویم، واحد، ارقام، منطقه زمانی، تم، نشست‌های فعال | تغییر زبان ← پیش‌نمایش `dir` فوری | API-PRO-001/002، API-AUTH-004، API-AUTH-007، API-AUTH-008 | PRO-001 |
| PG-BODY-001 Body | `/app/body` | آخرین اندازه‌ها، نمودار روند، BMI/WHtR با برچسب «شاخص غربالگری»، فرم ثبت (واحد، روش، تخمین/اندازه‌گیری) | Empty: بدون داده؛ هشدار «تغییر کمتر از خطای اندازه‌گیری» | API-BODY-001/002 | BODY-001 |
| PG-HEALTH-001 Health & Limitations | `/app/health` | فهرست مواردِ ثبت‌شده با وضعیت، افزودن/ویرایش، ثبت درد، وضعیت ارجاع، آخرین SafetyDecision | بدون رضایت: ConsentGate؛ ثبت آفلاین غیرفعال (بنر) | API-HEALTH-001..007 | HEALTH-001، SAFE-* |
| PG-EX-001 Library | `/app/exercises` | جست‌وجو/فیلتر (عضله، تجهیزات، سطح، الگو)، کارت‌ها، pagination | Empty: بدون نتیجه (پیشنهاد حذف فیلتر)؛ بدون محتوای published: پیام «محتوا در حال بازبینی» | API-EX-001 | EX-001 |
| PG-EX-002 Detail | `/app/exercises/[id]` | رسانه (یا «بدون رسانه»)، عضلات، تجهیزات، مراحل، تنفس، خطاها، ایمنی، سازگاری با شما (allowed/caution/blocked + دلیل)، جایگزین/رگرسیون/پروگرشن، ست/تکرار برنامه (اگر در برنامه) | blocked: نمایش علت و جایگزین؛ «جایگزین نداریم» | API-EX-002/003 | EX-002، WO-003 |
| PG-WO-001 Plan | `/app/plan` | برنامه فعال: روزها، حرکات، ست‌ها، دلیل انتخاب، سطح اطمینان، نسخه‌ها، دکمه جایگزینی/تولید مجدد | Empty/NEEDS_INFO: پرسش‌ها؛ STOP: صفحه ایمنی؛ NEEDS_CONTENT: پیام | API-WO-001..004 | WO-001..004 |
| PG-WO-002 Session | `/app/session/[id]` | نمای تمرین‌محور: حرکت جاری، ردیف‌های ست (ورودی بزرگ وزنه/تکرار/RPE)، تایمر استراحت، «جایگزین»، «درد؟» (کاهش/جایگزین/توقف)، پایان | نبود اینترنت: طبق ADR-0004 (flag)؛ ذخیره idempotent با client_uuid؛ «درد» ← API-HEALTH-005 آنلاین و ممکن است STOP | API-LOG-001..003، HEALTH-005 | LOG-001/002، SAFE-007 |
| PG-LOG-001 History | `/app/history` | فهرست جلسات، جزئیات، رکوردها | Empty | API-LOG-004 | LOG-003 |
| PG-PROG-001 Progress | `/app/progress` | گزارش هفتگی/ماهانه (ماهانه با گیت پلن غیرایمنی)، نمودارها با جدول جایگزین | 402 → پیام ارتقا (غیر ایمنی) | API-PROG-001/002 | DASH-001 |
| PG-SUB-001 Subscription | `/app/subscription` | پلن فعلی، قابلیت‌ها/سهمیه، لغو؛ «ایمنی همیشه رایگان»؛ Checkout: Provider پیکربندی‌نشده ← 501 با پیام | — | API-SUB-002..004 | SUB-001/002 |
| PG-PRIV-001 Privacy & Data | `/app/privacy` | رضایت‌ها (مشاهده/لغو)، Export، حذف حساب (تأیید دو مرحله‌ای + رمز)، وضعیت درخواست‌ها | لغو رضایت: توضیح اثر | API-PRIV-001..005 | PRIV-001..003 |
| PG-AI-001 Coach | `/app/coach` | (flag) چت توضیحی، نمایش منبع/عدم قطعیت، حالت fallback | غیرفعال: صفحه «به‌زودی» | API-AI-001 | AI-001 |
| Deferred | Nutrition Plan، Food DB، Recipe، Check-in، Recovery، Budget، Calendar، Education، Notifications | Deferred طبق DOC-18 | — | — | — |

## ۴. پنل ادمین (`/admin`) — طراحی با همان Design System
| PG | هدف | نقش | API |
|---|---|---|---|
| PG-ADM-001 Exercises | فهرست/ایجاد/ویرایش حرکت؛ چک‌لیست انتشار (۱۵ ناحیه، رسانه، منبع)؛ گذار گردش؛ گزارش پوشش | content_admin, exercise_reviewer, clinical_safety_reviewer | API-ADM-001..003 |
| `PG-ADM-002 Safety Rules` | نسخه‌های قواعد، مقایسه، انتشار (فقط Reviewer)، نمایش وضعیت EXP | clinical_safety_reviewer | API-ADM-004/005 |
| PG-ADM-003 Users | فهرست کاربران بدون داده سلامت؛ اعطای grant زمان‌دار | support_admin, super_admin | API-ADM-006/007 |
| PG-ADM-004 Plans | ماتریس قابلیت-پلن؛ toggleهای safety_critical قفل | super_admin, finance_admin | API-ADM-008 |
هر اقدام حساس: تأیید و ثبت ممیزی؛ دسترسی غیرمجاز: AccessDenied.

## ۵. جریان‌های کلیدی
1. **اولین استفاده:** Landing → Register → Verify → Onboarding(رضایت+غربالگری) → [ALLOW] Plan → Session → Dashboard.
2. **Red flag:** غربالگری مثبت → صفحه ایمنی (STOP_AND_REFER) → Dashboard فقط با بنر + اطلاعات؛ بدون CTA تمرین.
3. **محدودیت کمر (مسیر A):** ثبت Condition (ناحیه=کمر) → پرسش‌های ناحیه‌ای → ALLOW_WITH_MODIFICATION → برنامه با حرکات سازگار + «جایگزین نداریم» در صورت نبود.
4. **درد حین تمرین:** SetRow → «درد» → انتخاب (کاهش/جایگزین/توقف) → در صورت تشدید STOP.
5. **حذف داده:** Privacy → حذف → تأیید → وضعیت.

## ۶. معیارهای پذیرش UI
| ID | معیار |
|---|---|
| AC-UI-001 | هر صفحه ۴ حالت Loading/Empty/Error/Denied دارد (تست Playwright) |
| AC-UI-002 | هیچ CTA تمرین در حالت STOP/BLOCK نیست |
| AC-UI-003 | تغییر زبان ← `dir` و تاریخ‌ها فوراً درست |
| AC-UI-004 | Session با صفحه‌کلید/تاچ قابل استفاده؛ هدف لمس ≥ 44px |
| AC-UI-005 | صفحات Health بدون رضایت محتوا نشان نمی‌دهند |

</div>

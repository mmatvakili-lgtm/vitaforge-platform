<div dir="rtl">

# MVP_GAP_ANALYSIS — فاصله واقعی تا MVP قابل استفاده

| فیلد | مقدار |
|---|---|
| Document ID | DOC-GAP |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-08 |

## ۱. خلاصه صریح

- وضعیت فعلی: **پروتوتایپ منطق دامنه + API توسعه**، نه MVP قابل استفاده.
- هیچ‌چیز `Production Ready` نیست. با `allow_unreviewed_content=False` (حالت production) هر درخواست برنامه تمرینی مسدود می‌شود (`SAF-R013`)، چون هیچ حرکت بازبینی‌شده‌ای وجود ندارد. این رفتار عمدی و درست است.
- مهم‌ترین مانع: **داده حرکات بازبینی‌شده** و **بازبینی متخصص**. هیچ‌کدام را نمی‌توان با کد حل کرد.
- شواهد این سند از اجرای واقعی در ۲۰۲۶-۱۱-۰۸ گرفته شده: ۲۸۰ تست سبز (`python3 -m pytest -q`، حدود ۴٫۵ ثانیه)؛ `python3 -m devserver` بالا آمد و `/api/v1/health/live`=۲۰۰، ثبت‌نام، و `/`=۲۰۰ را جواب داد.

## ۲. سطح هر ماژول

سطح‌ها دقیقاً چهار مقدار هستند: `Designed`، `Implemented`، `Tested`، `Runtime Verified`. هر سطح شامل سطح‌های پایین‌تر است. «Runtime Verified» یعنی در اجرای واقعی (نه فقط تست واحد) دیده شده؛ هیچ ماژولی روی زیرساخت واقعی (PostgreSQL، مرورگر واقعی) اجرا نشده.

| ماژول | سطح | تست‌ها | توضیح محدودیت |
|---|---|---|---|
| `safety_core` | `Runtime Verified` (در `devserver`) | ۷۹ | قواعد بالینی `Draft`؛ مسیر B غیرفعال؛ پارامترها بدون تأیید متخصص (`EXP-001..013`) |
| `workout_engine` | `Runtime Verified` (در `devserver`) | ۶۱ | جدول prescription و progression با برچسب `Unverified`؛ برنامه همیشه `experimental` |
| `exercise_catalog` | `Tested` | ۱۴ | ۲۵ حرکت نمونه، همه `experimental`؛ `publishable == []`؛ importer فقط با داده ساختگی تست شده |
| `nutrition_engine` | `Tested` | ۱۴ | فرمول Mifflin–St Jeor؛ ماکرو/آب `Unverified`؛ هدف عددی کاهش/افزایش وزن غیرفعال تا `bounds_reviewed` (`EXP-006`)؛ پایگاه غذا وجود ندارد |
| `ai_gateway` | `Tested` | ۳۷ | فقط `StubProvider`؛ در production «unconfigured» و fallback؛ ارسال داده سلامت به بیرون ممنوع (`OPEN-002`) |
| `entitlements` | `Tested` | ۴ | قفل نبودن قابلیت‌های ایمنی تست شده؛ پوشش تست کم |
| `app_services` | `Runtime Verified` (در `devserver`، حافظه‌ای) | ۳۵ | ذخیره‌سازی فقط in-memory؛ پرداخت `DisabledPaymentProvider` |
| `devserver` | `Runtime Verified` | ۱۸ | فقط توسعه؛ تطابق OpenAPI فقط از نظر وجود مسیر |
| `e2e` (سناریوها) | `Tested` | ۸ | روی `devserver`/سرویس‌ها، بدون مرورگر |
| `config` + `apps/core` (Django) | `Implemented` | ۱۰ | Django نصب/اجرا نشده؛ هیچ migration ای وجود ندارد (پوشه `migrations` خالی/ناموجود) |
| `frontend` (Next.js) | `Designed` | ۰ | چند فایل اسکلت؛ `npm install`/build اجرا نشده |
| صفحه ایستای فارسی (در `devserver`) | `Runtime Verified` (فقط HTTP ۲۰۰) | ۰ | بدون تست مرورگر؛ رفتار UI تأیید نشده |
| Docker / compose / CI | `Implemented` | ۰ | هرگز اجرا نشده؛ CI روی GitHub هرگز اجرا نشده |

## ۳. فهرست Mock / Stub / Experimental / غیرفعال

| مورد | محل | وضعیت |
|---|---|---|
| `StubProvider` هوش مصنوعی | `ai_gateway/providers.py` | Mock؛ تولید متن واقعی ندارد |
| `DisabledPaymentProvider` | `app_services/subscriptions.py` | غیرفعال (`PreconditionRequired`) |
| ذخیره‌سازی in-memory | `devserver/app.py` | موقت؛ داده با ری‌استارت از بین می‌رود |
| `allow_unreviewed_content` / `dev_experimental` | `devserver/__main__.py`، `bridge` | فقط توسعه؛ RuleSet نسخه ۰ `dev-demo` |
| `caution_max_loading="low"` در E2E | `e2e/` | جایگزین `EXP-002`؛ پیش‌فرض واقعی `"none"` |
| مسیر B (درد جدید/نامشخص) | `safety_core` | غیرفعال (`STOP_AND_REFER`) تا `path_b_activity_rules_published` |
| `supports_regions` (حرکات حمایتی) | `exercise_catalog`، `workout_engine` | فقط زیرساخت؛ بدون داده بالینی (`OPEN-008`) |
| هدف عددی تغییر وزن | `nutrition_engine` | غیرفعال تا `EXP-006` |
| ایمیل/SMS بازیابی رمز | `app_services/more.py` | فرض: توکن تولید می‌شود، ارسال واقعی وجود ندارد (`Not Run`) |

## ۴. شکاف داده حرکات

- موجود: ۲۵ حرکت نوشته‌شده توسط خودمان؛ `evidence_level=none`، `expert_review=pending`، `safety_tags_status=unreviewed_estimate`، `is_sample=True`.
- پوشش الگوی حرکتی: squat ۴، hinge ۲، push_horizontal ۳، push_vertical ۲، pull_horizontal ۲، pull_vertical ۲، lunge ۳، core ۴، carry ۱، other ۲. **حرکت کشش بدون وسیله (bodyweight pull) وجود ندارد**؛ کاربر خانگی بدون تجهیزات به `NEEDS_CONTENT` می‌خورد.
- حداقل داده لازم برای MVP: به‌ازای هر الگوی حرکتی و هر سطح تجهیزات، چند حرکت با برچسب ایمنی `reviewed`. عدد دقیق را متخصص تعیین می‌کند؛ ما فقط ظرفیت فنی را فراهم کرده‌ایم.

### مجوز منابع جایگزین (بررسی ۲۰۲۶-۱۱-۰۸؛ هیچ داده‌ای Import نشد)

| منبع | یافته | وضعیت |
|---|---|---|
| `yuhonas/free-exercise-db` | Unlicense (مخزن)؛ مبدأ داده `wrkout/exercises.json` | مجوز مخزن تأیید شد؛ **مجوز بالادست و تصاویر: `unverified`** |
| `wrkout/exercises.json` | صفحه شخص ثالث می‌گوید Unlicense و بدون محدودیت تجاری؛ منبع اصلی متن/تصاویر ذکر نشده | `unverified` (نیاز به بررسی حقوقی) |
| wger | نرم‌افزار AGPL-3+؛ داده حرکات CC BY-SA 3.0 (share-alike) | نیازمند بررسی حقوقی (`OPEN-004`) |
| `USDA FoodData Central` | Public Domain / CC0 1.0؛ درخواست ذکر منبع (الزام نیست) | مناسب برای پایگاه غذا؛ پوشش غذاهای ایرانی ضعیف است |
| `Open Food Facts` | پایگاه داده ODbL، محتوا DbCL، تصاویر CC BY-SA؛ شرایط ذکر منبع و share-alike | نیازمند بررسی حقوقی؛ تصاویر را وارد نکنید |

نکته مهم: **حتی با مجوز آزاد، داده وارد‌شده `pending_review` می‌ماند.** مجوز مشکل حقوقی را حل می‌کند، نه مشکل صحت بالینی/ایمنی را.

## ۵. جدول شکاف به‌تفکیک قابلیت

| قابلیت | داریم | نداریم | اقدام | وابستگی |
|---|---|---|---|---|
| هسته ایمنی | موتور، explain FA/EN، fail-safe، ۷۹ تست | قواعد بالینی تأییدشده، مسیر B | افزودن قواعد فقط پس از تأیید | متخصص |
| برنامه تمرین | pipeline S0..S7، ساختارها، progression | prescription تأییدشده، داده کافی | اتصال به کاتالوگ واقعی | داده + متخصص |
| کاتالوگ حرکات | schema، importer، گردش‌کار انتشار | حرکت `published` | تهیه/بازبینی داده | متخصص + حقوقی |
| تغذیه | محاسبه انرژی، فیلتر آلرژی، لاگ | پایگاه غذا، کران‌های تأییدشده | انتخاب منبع غذا (`USDA`) و Import | حقوقی + متخصص |
| AI | gateway، validator، `DecisionLayer` | Provider واقعی | تصمیم `OPEN-002`، سپس کانکتور | حقوقی/تجاری |
| Backend واقعی | Django skeleton | اجرا، migration، PostgreSQL | نصب و اجرا در محیط دارای شبکه | شبکه |
| Frontend | صفحه ایستای dev، اسکلت Next.js | build، صفحات، E2E مرورگر | نصب Node، پیاده‌سازی | شبکه |
| پرداخت | رابط + نسخه غیرفعال | Provider | `OPEN-001/005` | تجاری |
| حریم خصوصی | export/erase، consent append-only | بازبینی حقوقی، قانون‌گذاری | `OPEN-004` | حقوقی |

## ۶. موانع MVP (Blocker)

1. حرکات `published` با برچسب ایمنی بازبینی‌شده (`OPEN-003/007`).
2. تأیید متخصص برای پارامترهای ایمنی/تمرین (فهرست در بخش ۹).
3. اجرای واقعی Django + PostgreSQL + migration (محیط دارای شبکه).
4. Frontend واقعی متصل به Backend واقعی و یک سناریوی مرورگر موفق.
5. بررسی حقوقی مجوز داده و ارسال داده سلامت (`OPEN-002/004`).

## ۷. قابل‌تعویق به بعد از MVP

پرداخت (`OPEN-001/005`)، Provider واقعی AI، مسیر B فعال، محتوای حمایتی/ریکاوری (`OPEN-008`)، هدف عددی کاهش/افزایش وزن، غذاهای ایرانی، PWA آفلاین.

## ۸. فعالیت‌های موازی

- **بدون وابستگی به انسان یا شبکه (قابل انجام همین حالا):** اعتبارسنجی کامل schema پاسخ‌ها در برابر OpenAPI؛ افزودن حرکت کشش بدون وسیله به قالب داده (فقط ساختار، نه محتوای تأییدشده)؛ تست‌های بیشتر `entitlements`؛ ابزار گزارش پوشش.
- **نیازمند شبکه (خارج از این محیط):** نصب Django/Node، اجرای CI.
- **نیازمند متخصص/حقوقی (موازی با کار فنی):** بازبینی داده، پارامترها، مجوزها.

## ۹. موارد نیازمند متخصص (کمینه؛ هیچ‌کدام به صاحب پروژه واگذار نشده)

صاحب پروژه پزشک نیست؛ این موارد باید به متخصص واجد صلاحیت (مثلاً فیزیوتراپیست/پزشک ورزشی/متخصص تغذیه) ارجاع شوند و تا آن زمان در وضعیت `Draft` بمانند:

| مورد | شناسه | دامنه |
|---|---|---|
| سقف بارگذاری ناحیه محتاط (`caution_max_loading`) | `EXP-002` | ایمنی تمرین |
| برچسب‌های ایمنی هر حرکت (`region_loads`، موارد منع) | `OPEN-003/007` | کاتالوگ |
| قواعد مسیر B | `EXP-001` | ارجاع/فعالیت |
| جدول prescription و progression | `EXP-013` | برنامه‌ریزی تمرین |
| کران‌های ماکرو/آب/تغییر وزن | `EXP-006` | تغذیه |
| محتوای حمایتی/ریکاوری | `OPEN-008` | بازتوانی |

بقیه (مجوز داده، حقوقی) به مشاور حقوقی ارجاع می‌شود، نه به متخصص بالینی. هیچ تأیید متخصصی در این مخزن جعل نشده است.

## ۱۰. تست پذیرش به‌ازای هر قابلیت

| قابلیت | تست پذیرش | وضعیت امروز |
|---|---|---|
| ایمنی | هر ورودی خطرناک ⟵ `STOP_AND_REFER`/`BLOCK`؛ خطای داخلی ⟵ `ERROR_FAILSAFE` | `Passed` (۷۹ تست) |
| برنامه تمرین | ۱۰ پروفایل نماینده، همه با داده `published` ⟵ برنامه معتبر یا `NEEDS_CONTENT` گویا | `Not Run` (داده published نیست) |
| کاتالوگ | Import ⟵ `pending_review` ⟵ گردش‌کار ⟵ `published` فقط با نقش متخصص | `Passed` (با داده ساختگی) |
| تغذیه | فیلتر آلرژی، ارجاع ED، دامنه عدم قطعیت | `Passed`؛ پایگاه غذا `Not Run` |
| API | هر ۵۶ endpoint وجود دارد و پاسخ مطابق schema است | وجود مسیر `Passed`؛ schema کامل `Not Run` |
| Backend واقعی | `manage.py migrate` + `check` روی PostgreSQL | `Not Run` |
| Frontend | ثبت‌نام ⟵ onboarding ⟵ دریافت برنامه ⟵ ثبت جلسه در مرورگر (Playwright) | `Not Run` |
| حریم خصوصی | export و erase کاربر، consent غیرقابل ویرایش | `Passed` (in-memory) |

## ۱۱. معیار عینی تکمیل MVP

MVP «کامل» اعلام نمی‌شود مگر **همه** این موارد درست باشند:

1. حداقل یک ماتریس تعیین‌شده‌ی حرکات `published` موجود است و `publishable` نگهدارنده نیست؛ هر حرکت امضای بازبینی متخصص (با مرجع مستند) دارد.
2. `allow_unreviewed_content=False` و برنامه واقعی برای پروفایل‌های نماینده تولید می‌شود.
3. `manage.py migrate` و تست‌ها روی PostgreSQL واقعی موفق است.
4. سناریوی E2E مرورگر (ثبت‌نام تا ثبت جلسه) روی Next.js ساخته‌شده موفق است.
5. CI روی GitHub سبز است.
6. همه موارد بخش ۹ و `OPEN-002/004` بسته یا صراحتاً با feature flag خاموش‌اند.
7. `RELEASE_CHECKLIST.md` هیچ `Blocked`/`Not Run` برای قابلیت‌های داخل MVP ندارد.

## ۱۲. محدودیت‌های این ارزیابی

- مجوزها از صفحات وب بررسی شد، نه متن کامل مجوز مخزن‌ها؛ برای انتشار، بازبینی حقوقی لازم است.
- پوشش تست اندازه‌گیری نشده (فقط تعداد تست).

</div>

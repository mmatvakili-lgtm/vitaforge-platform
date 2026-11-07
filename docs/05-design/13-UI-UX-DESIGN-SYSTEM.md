<div dir="rtl">

# سند ۱۳ — `UI/UX Design System`

| فیلد | مقدار |
|---|---|
| Document ID | DOC-13 |
| Version | 0.1 |
| Status | Draft — Complete (توکن‌ها و کامپوننت‌ها)؛ طراحی بصری Wireframe/Hi-fi: In Progress (در DOC-14 توصیف متنی) |
| Created / Updated | 2026-11-07 |
| Owner | UI/UX Designer |
| Related Documents | DOC-14، DOC-01 (I18N)، DOC-15 |
| Related Decisions | DEC-003؛ NFR-A11Y-001 |

## 1. جهت هنری
Premium، Modern، Scientific، Minimal، اعتمادآفرین. نه پنل مدیریتی خام. فضای سفید سخاوتمند، سلسله‌مراتب تایپوگرافی قوی، رنگ معنایی ثابت، انیمیشن هدفمند (≤ 200ms، احترام به `prefers-reduced-motion`).

## 2. توکن‌ها (CSS variables؛ Light/Dark)
### رنگ
| توکن | Light | Dark | کاربرد |
|---|---|---|---|
| `--bg` | #F7F8F6 | #0E1311 | زمینه صفحه |
| `--surface` | #FFFFFF | #151C19 | کارت |
| `--surface-2` | #EEF1EE | #1C2521 | سطح دوم |
| `--text` | #121815 | #EAF0EC | متن اصلی |
| `--text-muted` | #516058 | #9DAEA5 | متن ثانویه |
| `--primary` | #0F766E | #2DD4BF | اقدام اصلی (سبز-فیروزه‌ای علمی) |
| `--primary-contrast` | #FFFFFF | #06201C | متن روی primary |
| `--accent` | #C2410C | #FB923C | تأکید/پیشرفت |
| `--border` | #D5DBD7 | #2A3631 | مرز |
| `--success` | #15803D | #4ADE80 | موفقیت |
| `--warning` | #A16207 | #FACC15 | احتیاط |
| `--danger` | #B91C1C | #F87171 | خطا/توقف ایمنی |
| `--safety` | #1D4ED8 | #60A5FA | پیام‌های ایمنی/ارجاع (متمایز از خطا) |
قانون: رنگ‌های `--danger/--warning/--safety` فقط معنای ثابت دارند؛ هرگز تنها حامل معنا نیستند (آیکون+متن). تضاد متن/زمینه ≥ 4.5:1 (۳:۱ برای متن بزرگ)؛ در تست a11y بررسی می‌شود.
### تایپوگرافی
- فارسی: Vazirmatn (یا Estedad)؛ انگلیسی: Inter؛ اعداد: ترجیح کاربر (`digit_style`). فونت‌ها self-host (بدون وابستگی CDN؛ مجوز OFL).
- مقیاس: 12/14/16/18/20/24/30/38/48؛ line-height متن ۱٫۶ (فارسی) / ۱٫۵؛ وزن 400/500/700.
### فاصله و شبکه
- واحد پایه ۴px؛ توکن‌ها `space-1..12` (4،8،12،16،20،24،32،40،48،64،80،96).
- Grid: ۴ ستون موبایل (<640)، ۸ تبلت (640–1024)، ۱۲ دسکتاپ؛ gutter 16/24؛ حداکثر عرض محتوا 1200px.
- Breakpoints: `sm 640`، `md 768`، `lg 1024`، `xl 1280`.
### شعاع/سایه/حرکت
شعاع 8/12/16؛ سایه نرم دو سطح؛ `--ease: cubic-bezier(.2,.8,.2,1)`.

## 3. RTL/LTR
- فقط **Logical Properties** (`margin-inline-start`، `padding-inline`، `inset-inline`، `text-align: start`)؛ `dir` روی `<html>`.
- آیکون‌های جهت‌دار (پیکان، chevron) در RTL آینه می‌شوند؛ آیکون‌های غیرجهت‌دار (play، ساعت) نه.
- متن دوطرفه: `<bdi>` برای نام‌های انگلیسی داخل متن فارسی؛ ارقام طبق ترجیح؛ واحدها LTR.
- نمودارها: محور زمان در RTL از راست به چپ.
- تقویم: شمسی/میلادی از ترجیح؛ شروع هفته (شنبه/دوشنبه) پیکربندی؛ ذخیره UTC.

## 4. کامپوننت‌ها (حالت‌ها و رفتار)
هر کامپوننت: default، hover، focus-visible (حلقه ۲px)، active، disabled، loading، error. اندازه لمس ≥ 44×44px.
| کامپوننت | نکات |
|---|---|
| Button (primary/secondary/ghost/danger) | loading spinner؛ غیرفعال با دلیل (tooltip/aria-describedby) |
| Input/Textarea/Select/Number | برچسب همیشه مرئی؛ خطا زیر فیلد با `aria-describedby`؛ واحد (kg/cm/lb/in) ثابت کنار فیلد؛ ورودی اعداد فارسی/لاتین هر دو پذیرفته می‌شود |
| Segmented/Radio/Checkbox/Switch | گروه‌بندی با `fieldset/legend` |
| Slider (RPE/درد 0–10) | مقدار عددی + برچسب متنی؛ معادل ورودی عددی برای a11y |
| DatePicker | شمسی/میلادی؛ تایپ دستی؛ تبدیل خودکار |
| Card | سربرگ، بدنه، اقدام؛ `Card.Safety` با آیکون و رنگ safety |
| Stepper/Progress | Onboarding ۱۴ مرحله‌ای، ذخیره خودکار |
| Tabs/Accordion/Drawer/BottomSheet | BottomSheet موبایل |
| Modal/Dialog | focus trap، Esc، `role=dialog`، بازگرداندن focus |
| Toast/Banner | موفقیت/خطا/اطلاع؛ بنر ایمنی دائمی (غیرقابل‌بستن تا اقدام) |
| Table/List | pagination سرور؛ مرتب‌سازی؛ در موبایل به کارت تبدیل |
| Chart (خط/میله/Sparkline) | رنگ‌های colorblind-safe + الگو/برچسب؛ جدول جایگزین قابل‌دسترس؛ حالت empty |
| Badge/Tag | وضعیت محتوا (Draft/Published)، سطح اطمینان |
| Skeleton/Spinner | برای Loading؛ skeleton با ابعاد نهایی (بدون پرش) |
| EmptyState | تصویر ساده + توضیح + اقدام |
| ErrorState | پیام کاربرپسند + کد درخواست + تلاش مجدد |
| AccessDenied | توضیح + مسیر (رضایت/ورود/پلن) |
| ExerciseCard/SetRow/RestTimer | مخصوص تمرین؛ SetRow با ورودی بزرگ برای استفاده حین ورزش |
| SafetyDecisionPanel | نمایش STOP/NEEDS_INFO/BLOCK با اقدام بعدی؛ متن از کلید i18n (محتوای Draft با برچسب) |
| ConsentGate | مانع نمایش داده سلامت تا رضایت |

## 5. الگوهای ناوبری
- موبایل: `Bottom Tab Bar` (امروز، برنامه، حرکات، پیشرفت، من) + Header ساده؛ دسکتاپ: Sidebar + Topbar.
- Breadcrumb در صفحات عمیق دسکتاپ؛ جهت ناوبری و FAB در RTL آینه.
- ناوبری ادمین جدا با ظاهر همان Design System.

## 6. حالت‌های سراسری
| حالت | رفتار |
|---|---|
| Loading | Skeleton؛ عملیات >۳s پیام پیشرفت |
| Empty | EmptyState با اقدام |
| Error | ErrorState + `request_id` |
| Offline | بنر «آفلاین»؛ داده سلامت غیرقابل ثبت با پیام صریح (ADR-0004) |
| Access denied/Consent required | AccessDenied/ConsentGate |
| Safety stop | صفحه تمام‌عرض با `--safety`، بدون CTA تمرین |

## 7. دسترس‌پذیری (WCAG 2.2 AA)
ناوبری کامل با کیبورد؛ ترتیب focus منطقی؛ لندمارک‌ها؛ `aria-live` برای toasts و نتیجه Safety؛ برچسب فرم؛ محتوا بدون وابستگی به رنگ؛ اندازه متن قابل‌تغییر تا 200٪؛ target size؛ کاهش حرکت؛ زبان صفحه (`lang`) و `dir` صحیح؛ ویدئو با زیرنویس (در صورت وجود).

## 8. لحن و میکروکپی
مهربان، علمی، بدون ادعای درمان؛ فارسی محاوره‌ای-رسمی ملایم؛ هرگز «درمان/ترمیم/تحمل کن». متن‌های ایمنی فقط از کلیدهای i18n بازبینی‌شده (محتوای Draft علامت‌دار).

## 9. پیاده‌سازی
Tailwind + CSS variables (توکن‌ها در `frontend/src/styles/tokens.css`)؛ کتابخانه کامپوننت داخلی (`frontend/src/ui/`)؛ آیکون: مجموعه SVG داخلی/OFL؛ تست بصری با Playwright screenshots (Light/Dark × RTL/LTR × موبایل/دسکتاپ).

## 10. معیارهای پذیرش
| ID | معیار |
|---|---|
| AC-DS-001 | همه صفحات فقط از توکن‌ها استفاده کنند (lint: بدون رنگ hex خام) |
| AC-DS-002 | هیچ CSS با `left/right` فیزیکی در کامپوننت‌ها (lint) |
| AC-DS-003 | تضاد رنگ طبق جدول در هر دو تم (تست خودکار) |
| AC-DS-004 | هر کامپوننت حالت‌های loading/error/empty را مستند و تست‌شده داشته باشد |

</div>

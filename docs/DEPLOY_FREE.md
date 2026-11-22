<div dir="rtl">

# استقرار رایگان نسخه‌ی عمومی (نمایشی)

> وضعیت: پیکربندی آماده است، اما **هنوز روی سرور واقعی اجرا و راستی‌آزمایی نشده**. اولین استقرار را مالک انجام می‌دهد؛ نتیجه را در `docs/ACCEPTANCE_CHECKLIST.md` ثبت کن.

## واقعیت‌های سرویس‌ها (بررسی‌شده در ۱۵ نوامبر ۲۰۲۶؛ ممکن است عوض شوند)

- **Render (بک‌اند):** ۷۵۰ ساعت رایگان در ماه، بعد از ۱۵ دقیقه بیکاری می‌خوابد (بیدار شدن حدود یک دقیقه)، دیسک موقت است، پورت‌های SMTP بسته است. دیتابیس رایگان خود Render بعد از ۳۰ روز منقضی می‌شود، پس استفاده نمی‌شود. Render خودش می‌گوید برای محصول تولیدی نیست.
- **Neon (دیتابیس):** رایگان، ۱ گیگابایت برای هر پروژه، ۱۰۰ ساعت محاسبه در ماه، بعد از ۵ دقیقه بیکاری به صفر می‌رسد.
- **Vercel Hobby (فرانت):** رایگان، فقط استفاده‌ی شخصی و غیرتجاری.
- **تلگرام:** رایگان؛ کانال تأیید حساب. ایمیل استفاده نمی‌شود.

## قدم‌ها

۱. **Neon:** در neon.com با GitHub ثبت‌نام کن، یک پروژه بساز (منطقه‌ی نزدیک اروپا)، و رشته‌ی اتصال را کپی کن (باید به `?sslmode=require` ختم شود). این رشته محرمانه است؛ در چت یا گیت نگذار.

۲. **Render:** در render.com با GitHub وارد شو، New ← Blueprint، مخزن `vitaforge-platform` را انتخاب کن. فایل `render.yaml` سرویس `vitaforge-api` را می‌سازد. این مقادیر را در داشبورد وارد کن:
   - `DATABASE_URL` = رشته‌ی Neon
   - `ALLOWED_HOSTS` = آدرس سرویس بدون `https://` (مثل `vitaforge-api.onrender.com`)
   - `FRONTEND_BASE_URL` = بعد از قدم ۳ آدرس Vercel
   - `TELEGRAM_BOT_TOKEN`، `TELEGRAM_BOT_USERNAME`، `TELEGRAM_WEBHOOK_SECRET` (توکن **جدید** بات؛ راز: ۳۲ نویسه‌ی تصادفی از `A-Z a-z 0-9 _ -`)

۳. **Vercel:** در vercel.com با GitHub وارد شو، Add New ← Project، همین مخزن، **Root Directory = `frontend`**. در Environment Variables بگذار: `BACKEND_URL` = `https://<آدرس Render>`. Deploy. بعد آدرس Vercel را در `FRONTEND_BASE_URL` Render بگذار.

۴. **وب‌هوک تلگرام:** وقتی Render سبز شد، در Shell همان سرویس (یا روی سیستم خودت با همان متغیرها) اجرا کن:
   `python manage.py telegram_set_webhook --url https://<آدرس Render>`

۵. **بررسی:** `https://<آدرس Render>/api/v1/health/ready` باید `content_mode: ai_curated_demo` نشان دهد؛ سپس ثبت‌نام و تأیید با تلگرام را روی آدرس Vercel امتحان کن. اولین درخواست بعد از بیکاری کند است.

## محدودیت‌های شناخته‌شده

- محتوای حرکت‌ها **تأییدنشده توسط متخصص** است و بنر نسخه‌ی نمایشی همیشه دیده می‌شود.
- محدودکننده‌ی نرخ per-IP روی لبه وجود ندارد (نیازمند دامنه و CDN).
- Render رایگان ممکن است هر لحظه ری‌استارت شود؛ داده‌ها در Neon می‌مانند.
- بک‌آپ خودکار نداریم؛ `manage.py backup_db` را دستی اجرا کن.

## مسیر بدون کارت بانکی: بک‌اند هم روی Vercel (پیشنهاد نهایی)

Hugging Face برای Docker پولی شد و Render کارت واقعی می‌خواهد. Vercel از Django پشتیبانی بدون پیکربندی دارد ([مستندات](https://vercel.com/docs/frameworks/backend/django)): پروژهٔ جدا با Root Directory برابر `backend`. فایل `backend/vercel.json` هنگام Build دستور `migrate` را روی Neon اجرا می‌کند (متغیرها باید قبل از اولین Deploy تنظیم شده باشند).

- دو پروژهٔ Vercel: `vitaforge-api` (Root = `backend`) و `vitaforge` (Root = `frontend`، با `BACKEND_URL` برابر آدرس API).
- متغیرهای API همان جدول Space/Render است؛ `ALLOWED_HOSTS` باید دقیقاً دامنهٔ پروژهٔ API باشد (wildcard در production ممنوع است).
- بدون Shell و بدون دیسک ماندگار: آپلود فایل ادمین در این حالت ماندگار نیست؛ همهٔ داده‌ها در Neon است.
- وضعیت: روی سرور واقعی اجرا و راستی‌آزمایی نشده؛ اولین Deploy را مالک انجام می‌دهد.

## جایگزین Render بدون کارت بانکی: `Hugging Face Space`

اگر Render کارت بانکی خواست، بک‌اند را روی یک Space داکری رایگان Hugging Face بگذار (بدون کارت). Neon و Vercel بدون تغییر می‌مانند. هر push به `main` که `backend/` را عوض کند خودکار دیپلوی می‌شود (`.github/workflows/deploy-hf.yml`).

۱. در huggingface.co ثبت‌نام کن. **New Space**: نام مثلاً `vitaforge-api`، SDK = **Docker** (Blank)، Hardware = CPU basic (رایگان)، Visibility = Public.
۲. در Settings ← Access Tokens یک توکن **Write** بساز و کپی کن (جایی منتشرش نکن).
۳. در GitHub مخزن: Settings ← `Secrets and variables` ← Actions:
   - تب Secrets: `HF_TOKEN` = توکن مرحله‌ی ۲.
   - تب Variables: `HF_SPACE` = `<نام‌کاربری>/vitaforge-api`.
۴. در Space: Settings ← `Variables and secrets.` این‌ها را به‌عنوان **Secret** اضافه کن: `DATABASE_URL`، `TELEGRAM_BOT_TOKEN`، `TELEGRAM_BOT_USERNAME`، `TELEGRAM_WEBHOOK_SECRET`، `DJANGO_SECRET_KEY` (یک رشته‌ی تصادفی بلند)، `ADMIN_BOOTSTRAP_EMAIL` (ایمیل خودت). و به‌عنوان **Variable**: `DJANGO_DEBUG=false`، `REDIS_URL=redis://unused.invalid:6379/0`، `VITAFORGE_CONTENT_MODE=ai_curated_demo`، `VITAFORGE_ACK_AI_CURATED_CONTENT=yes`، `AI_EXTERNAL_HEALTH_DATA=false`، `ALLOWED_HOSTS=<نام‌کاربری>-vitaforge-api.hf.space`، `FRONTEND_BASE_URL=https://<آدرس Vercel>`.
۵. در GitHub: Actions ← deploy-hf ← Run workflow (یا یک commit به `main`). بعد از چند دقیقه Space سبز (Running) می‌شود.
۶. در Vercel مقدار `BACKEND_URL` را `https://<نام‌کاربری>-vitaforge-api.hf.space` بگذار و Redeploy کن.
۷. وب‌هوک تلگرام را از سیستم خودت (PowerShell) با همان متغیرها اجرا کن: `python manage.py telegram_set_webhook --url https://<نام‌کاربری>-vitaforge-api.hf.space`
۸. بررسی: `https://<نام‌کاربری>-vitaforge-api.hf.space/api/v1/health/ready`.

نکته‌ها: Space رایگان بعد از مدتی بی‌کاری می‌خوابد و با اولین درخواست بیدار می‌شود؛ دیسک موقت است و داده‌ها در Neon می‌مانند. این مسیر از داخل این محیط اجرا یا آزمایش نشده و دسترسی به Hugging Face از ایران تأیید نشده است؛ اگر باز نشد، فیلترشکن یا گزینه‌ی SnapDeploy (بدون کارت، ۱۰۰ ساعت در ماه) را امتحان کن.

### حساب مدیریت بدون شل
Space شل ندارد. برای ساخت حساب «مدیریت»: متغیر `ADMIN_BOOTSTRAP_EMAIL` را (روی Render یا Space) برابر ایمیل خودت بگذار، با همان ایمیل در برنامه ثبت‌نام و تأیید کن، وارد شو و `/fa/admin` را باز کن. حسابِ **تأییدشده** با همین ایمیل فقط وقتی هنوز مدیریتی وجود ندارد مدیریت می‌شود؛ بعد از آن این متغیر هیچ اثری ندارد. روش دیگر (سیستم خودت): `create_staff --role super_admin`.

</div>

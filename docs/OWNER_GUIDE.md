<div dir="rtl">

# راهنمای گام‌به‌گام مالک: از صفر تا آماده‌ی استفاده

وضعیت: **Written, Not Run**. هر گام یک «معیار موفقیت» دارد؛ اگر نتیجه فرق داشت، خروجی کامل را بفرست. همه‌ی دستورها در PowerShell ویندوز و از پوشه‌ی `D:\vitaforge-platform` هستند.

## گام ۰ — آخرین کد و سلامت پایه

```
git pull
cd backend ; .\.venv\Scripts\Activate.ps1
python manage.py migrate
python -m pytest -q
cd ..\frontend ; npm ci ; npx tsc --noEmit ; npm run build
```

معیار موفقیت: pytest بدون failure، `tsc` بدون خروجی، `next build` موفق. (`npm audit fix --force` را نزن.)

## گام ۱ — اجرای محلی و حساب‌های کارمند

```
cd backend
powershell -File scripts\run.ps1                       # ترمینال ۱: بک‌اند روی 8000
cd ..\frontend ; npm run dev                           # ترمینال ۲: فرانت‌اند روی 3000
cd ..\backend
python manage.py create_staff --email admin@yourmail.com --password "یک-رمز-قوی" --role admin
python manage.py create_staff --email nutrition@yourmail.com --password "یک-رمز-قوی" --role nutrition_reviewer
```

معیار: `http://localhost:3000/fa` باز شود و با حساب admin بتوانی وارد شوی. رمزها را در جایی امن نگه دار، نه در گفت‌وگو.

## گام ۲ — ایمیل واقعی (SMTP)

۱. یک سرویس SMTP بگیر (مثلاً Brevo، Mailgun، Amazon SES، یا حساب Gmail با App Password) و دامنه‌ی فرستنده را تأیید کن.
۲. در فایل `.env` (کپی `.env.example`) مقادیر را بگذار: `MAIL_PROVIDER=smtp`، `SMTP_HOST`، `SMTP_PORT=587`، `SMTP_SECURITY=starttls`، `SMTP_USERNAME`، `SMTP_PASSWORD`، `MAIL_FROM_ADDRESS`، `FRONTEND_BASE_URL`.
۳. `python manage.py mail_status --send-test you@yourmail.com`

معیار: ایمیل تست در صندوق خودت برسد. سپس ثبت‌نام با ایمیل دیگر و رسیدن کد تأیید را امتحان کن. فقط بعد از این دو، وضعیت «ارسال واقعی ایمیل تأیید شد» درست است. فرایند ارسال: `python manage.py process_outbox` (یا سرویس `mail-worker` در docker-compose).

## گام ۳ — PostgreSQL واقعی

```
docker compose -f infra\docker-compose.yml up -d db redis
# در .env: DATABASE_URL=postgres://vitaforge:vitaforge@localhost:5432/vitaforge
cd backend
python manage.py migrate
$env:VITAFORGE_TEST_STORE="django"
$env:VITAFORGE_TEST_DATABASE_URL="postgres://vitaforge:vitaforge@localhost:5432/vitaforge_test"
python -m pytest -q
```

معیار: همه‌ی تست‌ها سبز روی Postgres. بعد پشتیبان‌گیری را امتحان کن:

```
python manage.py backup_db --out ..\backup-test.json
# سپس روی دیتابیس خالی دیگر: python manage.py restore_db --in ..\backup-test.json
```

فایل پشتیبان رمزنگاری‌شده نیست و داده‌ی سلامت دارد؛ آن را با ابزار رمزنگاری (مثلاً 7-Zip با رمز یا `age`) نگه دار و در Git نگذار.

## گام ۴ — داده‌ی غذا (`USDA FoodData Central`)

۱. از `https://fdc.nal.usda.gov/download-datasets` فایل **Foundation Foods (JSON)** را دانلود کن. مجوز آن را همان‌جا بخوان و یادداشت کن.
۲. آزمایش بدون ذخیره: `python manage.py import_foods --file C:\path\foundation.json --retrieved 2026-11-13 --dry-run`
۳. ذخیره: همان دستور بدون `--dry-run`. همه‌ی غذاها `pending_review` هستند و برای کاربران دیده نمی‌شوند.
۴. وارد `http://localhost:3000/fa/admin/review` شو. برای هر غذا: منبع را ببین؛ آلرژن‌ها را **خودت یا متخصص تغذیه** در منبع بررسی کن (از مغذی‌ها قابل حدس نیست)؛ «مجوز را بررسی کرده‌ام» فقط با حساب admin و پس از خواندن مجوز واقعی؛ سپس «تأیید».

معیار: دست‌کم چند غذای «بازبینی‌شده» در `/fa/foods` دیده شود و برنامه‌ی غذایی دیگر `NEEDS_CONTENT` نباشد. **توصیه:** تا بازبینی متخصص تغذیه انجام نشده، فقط برای آزمایش خودت تأیید کن و برای کاربر واقعی منتشر نکن.

## گام ۵ — داده‌ی حرکت‌ها

۱. وضعیت فعلی: ۸۷۶ حرکت منبع آزاد در `backend/exercise_catalog/data/staging/` به‌صورت **staging** است و بارگذاری نمی‌شود، چون مجوز تأیید نشده و برچسب‌های ایمنی بازبینی نشده‌اند.
۲. برای انتشار هر حرکت باید متخصص تمرین و مسئول ایمنی بالینی آن را از مسیر `draft → بازبینی علمی → بازبینی ایمنی → published` تأیید کنند (API مدیریتی موجود است؛ صفحه‌ی مدیریتی برای حرکت‌ها هنوز نیست).
۳. تا آن موقع برنامه‌ی تمرین کاربر واقعی `NEEDS_CONTENT` می‌ماند. این عمدی است.

## گام ۶ — امنیت و محیط production

- `DJANGO_SECRET_KEY` را با یک مقدار تصادفی بلند بگذار؛ `DJANGO_DEBUG=false`؛ `ALLOWED_HOSTS` را دامنه‌ی خودت بگذار.
- `npm audit` را اجرا کن و خروجی را بفرست تا بررسی کنیم.
- `AI_EXTERNAL_HEALTH_DATA=false` بماند.

## گام ۷ — بررسی دستی UI

روی موبایل و حالت راست‌به‌چپ: ثبت‌نام و تأیید ایمیل، onboarding، `/fa/foods`، `/fa/nutrition/log`، `/fa/history`، `/fa/profile` (دانلود داده‌ها و حذف حساب)، و نصب PWA. هر مورد ناجور را با اسکرین‌شات بفرست.

## گام ۸ — مواردی که فقط انسان‌های واجد صلاحیت تأیید می‌کنند

بازبینی متخصص تمرین، تغذیه و ایمنی بالینی؛ بررسی حقوقی (حریم خصوصی، شرایط استفاده، مجوز داده‌ها). تا انجام نشده، برنامه «آزمایشی» است و نباید توصیه‌ی پزشکی/تغذیه‌ای معرفی شود.

</div>

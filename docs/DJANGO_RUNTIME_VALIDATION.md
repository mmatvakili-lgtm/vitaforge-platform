<div dir="rtl">

# گزارش `Django Runtime Validation`

> نتیجه: **Not Run**. هیچ نتیجه‌ای ساختگی گزارش نشده است (DEC-150).

## چه چیزی اجرا نشد و چرا

| مورد | وضعیت | دلیل |
|---|---|---|
| نصب Django/DRF/psycopg | Not Run | محیط ابری شبکه ندارد؛ `pip` پکیجی پیدا نکرد |
| `migrate` روی PostgreSQL | Not Run | بدون Django؛ ضمناً migrationها هرگز تولید نشده‌اند (`makemigrations` اجرا نشده) |
| اعتبارسنجی ۵۶ عملیات روی Django | Not Run **و ممکن نیست** | لایه Django فقط `health/live`، `health/ready`، ۴ مدل و Bearer auth دارد؛ ۵۶ عملیات روی آن پیاده‌سازی نشده‌اند |
| تست امنیتی cookie/CSRF روی Django | Not Run | `settings.py` فقط Bearer دارد، نه cookie `sessionid` + `X-CSRFToken` که spec می‌خواهد |

## یافته‌های مهم (از خواندن کد، نه اجرا)

- `devserver` فقط یک آداپتور مبتنی بر `app_services` است؛ Django هنوز معادلی ندارد.
- `settings.py` احراز هویت Bearer دارد ولی spec و devserver از cookie + CSRF استفاده می‌کنند.
- مدل‌های Django کامل نیستند (مثلاً جدول پروفایل/برنامه/لاگ ندارند) و `Store` سرویس‌ها حافظه‌ای است.

## Runbook (روی سیستم دارای شبکه)

```
cd backend
pip install -r requirements.txt
python ../tools/django_preflight.py          # فقط PASS/FAIL واقعی چاپ می‌کند
docker compose -f ../infra/docker-compose.yml up -d db
set DATABASE_URL=postgres://...              # و بقیه متغیرهای REQUIRED
python manage.py makemigrations core ; python manage.py migrate
```

مراحل بعدی (کار توسعه، OPEN-013): لایه Store مبتنی بر ORM، ۵۶ view که همان سرویس‌ها را صدا بزنند، و اجرای `contract.harness.Harness` با کلاینت Django.

## نتیجه PostgreSQL

### PostgreSQL Integration: Not Run

- ثبت‌نام، ورود، پروفایل، داده سلامت، برنامه‌ها با ذخیره‌سازی واقعی: Not Run (لایه ذخیره‌سازی PostgreSQL وجود ندارد).
- ماندگاری پس از Restart، جداسازی کاربران، حذف حساب و Export روی DB واقعی: Not Run.
- منطق این موارد در سطح سرویس (حافظه‌ای) تست شده است: جداسازی کاربران، erase/export، idempotency.

### آنچه واقعاً اجرا شد

یک PostgreSQL 16 واقعی در همین محیط بالا آمد و **فقط** یک smoke در سطح SQL روی constraint انتشار حرکت اجرا شد (معادل SQL مدل، نه خروجی Django):

- درج `published` با `is_sample=true` رد شد.
- درج `published` با تگ ناقص رد شد.
- `UPDATE` گروهی به `published` رد شد.
- یک تراکنش دارای دستور ناموفق، `ROLLBACK` شد و فقط ردیف مجاز ماند.

این فقط صحت معنایی `CHECK` را نشان می‌دهد؛ تست یکپارچگی Django نیست.

## تفاوت devserver و Django

| جنبه | devserver | Django |
|---|---|---|
| عملیات API | ۵۶ از ۵۶ | ۰ (فقط health) |
| احراز هویت | cookie HttpOnly + CSRF | Bearer |
| ذخیره‌سازی | حافظه | ORM جزئی؛ migration نیست |
| Error envelope | مطابق spec | تعریف نشده (پیش‌فرض DRF) |
| وضعیت | Tested | Written, Not Run |

</div>

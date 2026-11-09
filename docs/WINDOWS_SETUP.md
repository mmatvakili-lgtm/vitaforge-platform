<div dir="rtl">

# راه‌اندازی محلی (Windows PowerShell)

وضعیت: **Written, Not Run**. این دستورات روی سیستم تو اولین بار اجرا می‌شوند؛ هر خطا را همراه خروجی کامل بفرست.

## پیش‌نیاز

- Python 3.12 تا 3.14، Git، و یکی از: Docker Desktop (PostgreSQL) یا SQLite برای آزمایش سریع.

## راه‌اندازی

```
git pull
docker compose -f infra\\docker-compose.yml up -d db redis      # اختیاری؛ برای SQLite لازم نیست
powershell -ExecutionPolicy Bypass -File backend\\scripts\\setup.ps1
powershell -File backend\\scripts\\run.ps1
```

برای آزمایش بدون Docker در `.env` بگذار: `DATABASE_URL=sqlite:///db.sqlite3`. سپس `http://127.0.0.1:8000/` (صفحه دمو با `VITAFORGE_DEV_CONTENT=true`).

## ساخت کاربر staff

```
cd backend
.\\.venv\\Scripts\\Activate.ps1
python manage.py create_staff --email admin@example.com --password "Str0ngPassw0rd" --role admin
```

## تست‌ها

```
cd backend
python -m pytest -q                                              # دامنه + قرارداد + پایداری SQLite
$env:VITAFORGE_TEST_STORE="django"                               # کل مجموعه روی Django ORM
$env:VITAFORGE_TEST_DATABASE_URL="postgres://vitaforge:vitaforge@localhost:5432/vitaforge_test"   # دیتابیس تست خالی (جداول پاک می‌شوند)
python -m pytest -q
```

## محدودیت‌های شناخته‌شده

- ارسال ایمیل ساخته نشده؛ در حالت production ثبت‌نام قابل تأیید نیست (OPEN).
- در production هیچ محتوایی Published نیست و Safety Core تولید برنامه را رد می‌کند؛ `VITAFORGE_DEV_CONTENT` فقط با `DJANGO_DEBUG=true` مجاز است.
- مهاجرت `0001_initial.py` دست‌نویس است؛ `makemigrations --check` باید «No changes» بدهد.

</div>

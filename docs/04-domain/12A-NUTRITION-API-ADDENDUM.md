<div dir="rtl">

# 12A — ضمیمه API تغذیه (پیاده‌شده در آداپتور توسعه)

| فیلد | مقدار |
|---|---|
| Document ID | DOC-12A |
| Version | 0.1 |
| Status | Draft |
| Updated | 2026-11-08 |

این مسیرها هنوز در `07-OPENAPI-SPECIFICATION.yaml` تولیدشده نیستند (اضافه‌کردن آن‌ها نیازمند تعریف schema در `tools/gen_openapi.py` است).

| مسیر | شرح |
|---|---|
| `POST /nutrition/estimate` | تخمین `BMR/TDEE` با بازه و عدم قطعیت؛ خروجی `OK/NEEDS_INFO/BLOCKED/REFER` |
| `POST /nutrition/meals` / `DELETE /nutrition/meals/{id}` | ثبت/حذف وعده (مقادیر وارد‌شده توسط کاربر) |
| `POST /nutrition/water` | ثبت آب |
| `GET /nutrition/summary` | خلاصه روز و مقایسه با بازه تخمین |
| `GET /safety/explain` | توضیح دلیل مجاز/محدود/رد برای هر حرکت |
| `GET /workouts/progression/{code}` | تصمیم پیشرفت قابل‌توضیح بر اساس تاریخچه |

فرمول: Mifflin–St Jeor (1990) × ضریب فعالیت پیکربندی‌شده؛ ضرایب، بازه ماکرو و آب `Unverified` (EXP-006)؛ هدف عددی کاهش/افزایش وزن غیرفعال.

</div>

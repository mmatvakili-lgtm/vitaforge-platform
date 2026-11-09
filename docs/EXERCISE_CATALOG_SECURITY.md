<div dir="rtl">

# گزارش امنیت Exercise Catalog

## مسیرهای ممکن برای Published و نتیجه بررسی

| مسیر | قبل | بعد |
|---|---|---|
| `CatalogService.transition` | زنجیره نقش + `tags_complete` خوداظهاری؛ **دور زدن ممکن** برای رکورد غیرنمونه | بدون `record` رد؛ `publication_blockers(record)` باید خالی باشد |
| Admin API (`ADM-002/003`) | `tags_complete` از کامل‌بودن `region_loads` ورودی ادمین؛ همیشه `is_sample` | بدون تغییر رفتار؛ تست منفی با تگ کامل و زنجیره کامل نقش‌ها: 409 |
| `bridge.to_candidate` | رکورد با ادعای `published` عیناً `published` می‌شد؛ **باگ** | ادعای مسدودشده به `pending_review` تنزل می‌یابد؛ `reviewed` بدون `expert_review=approved` کامل نیست |
| میان‌بر dev (`dev_experimental`) | بدون محافظ | در `VITAFORGE_ENV=production` خطا؛ `missing` هرگز ارتقا نمی‌یابد |
| Loader/دسته‌ها | رکورد `published` پذیرفته می‌شد | `ValueError` برای رکورد نامعتبر یا published با مانع؛ id تکراری رد |
| Importer | همیشه `pending_review`/`missing` | بدون تغییر؛ تست با ردیفی که ادعای published دارد |
| مدل Django `Exercise` | هیچ محدودیتی | `CheckConstraint` برای ORM/bulk/SQL/admin (Not Run در Django) |
| `assert_production_catalog` | موجود | بدون تغییر؛ تست شد |

## محدودیت‌ها

- سرویس فعلاً رکورد را از فراخواننده می‌گیرد؛ ثبت رکورد واقعی در مسیر ADM-002 هنوز وجود ندارد، بنابراین Admin API عملاً هیچ‌گاه حرکتی را منتشر نمی‌کند.
- `CheckConstraint` فقط شرط ساده را می‌پوشاند؛ مجوز/منبع/بازبینی در سرویس اعمال می‌شود.
- هیچ حرکتی Published نشده است و هیچ تأیید پزشکی ادعا نمی‌شود. وضعیت ایمنی و مجوز فقط از فیلدهای رکورد خوانده می‌شود، نه از وضعیت توسعه/تست.

## تست‌های جدید

`exercise_catalog/tests/test_publication_security.py` (۷ حالت پارامتری رد انتشار با زنجیره کامل نقش، رکورد نبودن، downgrade، loader، importer، guard تولید) و یک تست API در `contract/tests/test_contract_errors.py`.

</div>

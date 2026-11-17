<div dir="rtl">

# مجوزهای شخص ثالث (بخش سه‌بعدی)

| مؤلفه | مجوز | مسیر |
|---|---|---|
| three.js r170 | MIT | `frontend/public/vendor/three/` |
| Draco decoder | Apache-2.0 | `frontend/public/vendor/draco/` |
| مدل آناتومی (Z-Anatomy / BodyParts3D، آماده‌سازی free-muscles) | CC BY-SA 4.0 | `frontend/public/vendor/anatomy/anatomy.glb` |
| مانکن سه‌بعدی و ۵ کلیپ موشن‌کپچر (Mesh2Motion / `Quaternius Universal Animation Library`، به‌همراه گردآوری OpenGym3D) | CC0 1.0 | `frontend/public/vendor/anatomy/figure.glb` |
| `body-viewer.js`, `figure-viewer.js` (کد خودی) | هم‌مجوز پروژه | `frontend/public/vendor/` |

- متن اعلان کامل: `/vendor/NOTICE.txt` (در پاورقی سایت لینک شده است).
- **مورد باز (مالک/حقوقی):** الزامات «اشتراک‌گذاری به همان صورت» (SA) در CC BY-SA 4.0 برای مدل و آثار مشتق از آن باید بررسی حقوقی شود؛ این بررسی هنوز انجام نشده است.

</div>

<div dir="rtl">

## عکس‌های مرجع حرکات (`frontend/public/exercise-media`)

- منبع: مجموعه‌ی عمومی free-exercise-db (مجوز مخزن: Unlicense).
- منشأ و مجوز خود تصاویر مستقل‌اً تأیید نشده است؛ مالک پروژه در تاریخ 2026-11-16 این ریسک را برای سرور آزمایشی/دمو پذیرفته است.
- پیش از هر استفاده‌ی تجاری باید جایگزین یا حذف شود. (مورد باز حقوقی)

</div>

<div dir="rtl">

## داده‌ی غذایی دمو (`backend/nutrition_engine/data`)

- ترکیب غذاها: ردیف‌های بدون‌تغییر `USDA FoodData Central Foundation Foods` (طبق اعلام FDC دامنه‌ی عمومی/CC0؛ در این محیط مستقل‌اً بازبینی نشده)، از نسخه‌ی عمومی روی GitHub (`chris-wamae/json-filter`)، وارد‌شده با `fdc_import`. فقط «کربوهیدرات به‌روش تفاضل» با مقدار منفی ناچیز به ۰ و کالریِ غایب با ضرایب Atwater ۴/۴/۹ (با برچسب «محاسبه‌شده») ثبت می‌شود.
- روغن‌ها و کره در این دانلود مقدار درشت‌مغذی ندارند؛ در داده نیستند و کالری «کمی روغن» در دستورها محاسبه نمی‌شود (در متن دستور ذکر شده).
- نام فارسی، آلرژن‌ها، برچسب رژیم و دستورهای پخت را AI تنظیم کرده و بازبینی تخصصی نشده است؛ همه `pending_review` و در رابط «بازبینی‌نشده» نمایش داده می‌شوند. برچسب «حلال» برای مرغ/گوشت/ماهی فرضِ تأمین حلال (بازار ایران) است و روی رکورد یادداشت شده.
- قیمت‌ها ساخته نشده‌اند؛ بودجه فقط با قیمت واردشده‌ی کاربر محاسبه می‌شود.
- بازسازی: `python3 tools/build_demo_nutrition.py <foundationDownload.json>`

</div>

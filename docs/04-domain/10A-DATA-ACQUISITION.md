<div dir="rtl">

# 10A — منابع داده حرکات و تغذیه (Data Acquisition)

| فیلد | مقدار |
|---|---|
| Document ID | DOC-10A |
| Version | 0.1 |
| Status | Active |
| Updated | 2026-11-08 |
| Related | DOC-10، DOC-12، OPEN-004، OPEN-007 |

منابع در تاریخ ۲۰۲۶-۱۱-۰۸ از صفحه‌های رسمی بررسی شدند؛ هر مورد بررسی‌نشده `unverified` ثبت شده است. تصویر/ویدئوی بدون مجوز استفاده نمی‌شود.

| منبع | مجوز | استفاده تجاری | بازنشر | اعتبار علمی | تصمیم |
|---|---|---|---|---|---|
| [Project-authored starter text (AI-drafted)](n/a) | project-owned | بله | بله | none | `Allowed only as draft/experimental`; `never publishable without expert review` + sources |
| [yuhonas/free-exercise-db](https://github.com/yuhonas/free-exercise-db) | Unlicense (repo); image license not stated | unverified | unverified | unverified | Importer supported; do NOT import for publication until upstream provenance is verified; never use its images |
| [wger Workout Manager](https://wger.readthedocs.io/) | Software AGPL-3+; initial exercise data CC BY-SA 3.0; docs CC BY-SA 4+ | unverified | unverified | unverified | Not imported; blocked pending legal review (OPEN-004/007) |
| [Mifflin MD, St Jeor ST, Hill LA, Scott BJ, Daugherty SA, Koh YO. Am J Clin Nutr 1990;51(2):241-7](https://insight.jci.org/references/scholar/5796/B66) | published paper (citation only) | بله | خیر | peer-reviewed; population: healthy adults | `Used for BMR estimate with stated uncertainty` |

## جزئیات

### authored_unreviewed
- **کپی‌رایت:** `Written for this project`; `no third-party text copied.`
- **کیفیت:** `General knowledge only`; `NOT expert reviewed`; no citations.
- **بومی‌سازی:** `FA/EN names drafted`; FA unreviewed

### free_exercise_db
- **کپی‌رایت:** `README says data derives from wrkout/exercises.json whose own license/provenance was NOT verified`; images' `license not stated.`
- **کیفیت:** 800+ exercises; fields: id,name,force,level,mechanic,equipment,primaryMuscles,secondaryMuscles,instructions,category,images; force/mechanic/equipment incomplete.
- **بومی‌سازی:** English only

### wger
- **کپی‌رایت:** `CC BY-SA requires attribution and share-alike` (`derived databases must be shared under the same terms`) - `needs legal review before commercial use. Some images from Wikipedia with per-file SOURCES.`
- **کیفیت:** Community-maintained; `no clinical review stated.`
- **بومی‌سازی:** Multi-language (to verify)

### mifflin_1990
- **کپی‌رایت:** `Formula only is used` (`facts are not copyrightable`); `no text copied.`
- **کیفیت:** `Authors/journal/year verified from the cited page`; `volume/pages from prior knowledge` - `verify in PubMed.`
- **بومی‌سازی:** n/a

## نتیجه
- هیچ منبع بیرونی هنوز برای بانک «منتشرشده» تأیید نشده است؛ بانک فعلی ۲۵ حرکت `experimental` تولید پروژه است.
- ابزار Import (`exercise_catalog.importer`) آماده است و ورودی‌ها را همیشه `pending_review` با برچسب ایمنی `missing` وارد می‌کند.
- اقدام لازم: بررسی حقوقی `OPEN-004/007` و یافتن متخصص `OPEN-003` برای بازبینی برچسب‌های ایمنی.

</div>

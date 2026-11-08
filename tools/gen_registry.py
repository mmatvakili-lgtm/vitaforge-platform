import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from registry_data import C, CAP_COLS, D
ROOT = pathlib.Path(__file__).resolve().parent.parent / "docs"
esc = lambda s: str(s).replace("|", "\\|")
o = ["# DECISION_REGISTRY — ثبت مرکزی تصمیم‌ها", "", "| فیلد | مقدار |", "|---|---|", "| Document ID | DOC-DR |", "| Version | 0.1 |", "| Status | Active |", "| Updated | 2026-11-08 |",
     "| Generated | `python3 tools/gen_registry.py` از `tools/registry_data.py` |", "",
     "هیچ تصمیمی فقط در گفتگو نمی‌ماند؛ هر تصمیم جدید ابتدا در `tools/registry_data.py` ثبت می‌شود.", "", "## ۱. جدول خلاصه", "",
     "| شناسه | عنوان | تصمیم نهایی | وضعیت | وابستگی | تست پذیرش |", "|---|---|---|---|---|---|"]
for d in D:
    o.append(f"| {d[0]} | {esc(d[1])} | {esc(d[4])} | `{d[8]}` | {esc(d[9])} | {esc(d[10])} |")
o += ["", "## ۲. جزئیات", ""]
for d in D:
    o += [f"### {d[0]} — {d[1]}", f"- **شرح مسئله:** {d[2]}", f"- **گزینه‌های بررسی‌شده:** {d[3]}", f"- **تصمیم نهایی:** {d[4]}", f"- **دلیل انتخاب:** {d[5]}",
          f"- **تأثیر روی محصول:** {d[6]}", f"- **تأثیر روی دیتابیس و API:** {d[7]}", f"- **وضعیت:** `{d[8]}`", f"- **وابستگی‌ها:** {d[9]}", f"- **تست پذیرش:** {d[10]}", ""]
(ROOT / "DECISION_REGISTRY.md").write_text("\n".join(o), encoding="utf-8")
c = ["# CAPABILITY_STATUS — وضعیت واقعی قابلیت‌ها", "", "| فیلد | مقدار |", "|---|---|", "| Document ID | DOC-CAP |", "| Version | 0.1 |", "| Status | Active |", "| Updated | 2026-11-08 |", "",
     "راهنما: ✔ انجام‌شده، ◐ جزئی/نمونه، ✖ انجام‌نشده. این وضعیت‌ها جدا هستند: پیاده‌سازی ≠ تست‌شدن ≠ داده ≠ اعتبارسنجی ≠ آماده تولید ≠ تأیید تخصصی. ستون «Pending Expert Review» یعنی بدون بازبینی متخصص قابل‌اتکا نیست (✔ = هنوز منتظر بازبینی).", "",
     "| ماژول | " + " | ".join(CAP_COLS) + " | یادداشت |", "|---|" + "---|" * (len(CAP_COLS) + 1)]
for m, v, n in C:
    c.append(f"| {esc(m)} | " + " | ".join(v) + f" | {esc(n)} |")
c += ["", "«Production Ready» برای هیچ ماژولی ✔ نیست و تا بسته‌شدن موانع `OPEN-001..008` نخواهد بود."]
(ROOT / "CAPABILITY_STATUS.md").write_text("\n".join(c), encoding="utf-8")
print(len(D), len(C))

<div dir="rtl">

# ADR-0005 — pgvector برای RAG

| فیلد | مقدار |
|---|---|
| Status | Accepted (مشروط) |
| Date | 2026-11-07 |
| Owner | Architect |
| Related Decisions | DEC-123، ASM-004 |
| Related Documents | DOC-03، DOC-20 |

**انتخاب:** pgvector در همان PostgreSQL پشت `VectorStore` Interface؛ جدول‌های `kb_documents`/`kb_chunks` با نسخه و منبع.
**دلیل:** یک پایگاه برای backup، رمزنگاری و ممیزی؛ کمترین پیچیدگی.
**شرط ارزیابی (ابتدای Phase 4):** تأخیر p95 جستجو، حجم chunkها، کیفیت بازیابی روی مجموعه ارزیابی؛ اگر معیارها برآورده نشد، جایگزینی از طریق Interface.
**ریسک:** محدودیت مقیاس؛ کاهش: Interface و ایندکس مناسب. مستندات رسمی هنوز در `references/` ثبت نشده‌اند.

</div>

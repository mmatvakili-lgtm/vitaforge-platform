import re, sys
sys.path.insert(0,'.')
from schema_def import E, DEFERRED
tables={e['table']:e for e in E}
# validate FKs
rels=[]; errs=[]
for e in E:
    for f in e['fields']:
        p=f.split('|')
        assert len(p)==6,(e['table'],f)
        m=re.search(r'FK->(\w+)\.(\w+)',p[4])
        if m:
            tt=m.group(1)
            if tt not in tables: errs.append((e['table'],p[0],tt))
            rels.append((e['table'],p[0],tt,m.group(2),p[2],'PK' in p[4]))
if errs: print("FK ERRORS",errs); sys.exit(1)

mods={}
for i,e in enumerate(E): e['ent']=f"ENT-{i+1:03d}"; mods.setdefault(e['module'],[]).append(e)

hdr=lambda id_,title,extra:f"""# {title}

| فیلد | مقدار |
|---|---|
| Document ID | {id_} |
| Version | 0.1 |
| Status | Draft — Complete برای دامنه MVP (جداول Deferred فقط فهرست) |
| Created / Updated | 2026-11-07 |
| Owner | Database Architect |
| Related Documents | DOC-03، DOC-07، DOC-09، DOC-15 |
| Related Decisions | DEC-003، 004، 112، 121، 125، 126؛ ADR-0003، ADR-0004 |

{extra}
"""
# ---- ERD ----
o=hdr("DOC-05","سند ۵ — Database ERD","""## قواعد عمومی
- PostgreSQL ≥ ۱۴ (نیاز pgvector فقط Phase 4). همه PK ها `uuid` (`gen_random_uuid()` از pgcrypto). زمان‌ها `timestamptz` در UTC (DEC-003).
- مقدار اندازه‌گیری در SI همراه `unit`؛ تخمین جدا از اندازه‌گیری (`source`).
- حذف: حذف نرم برای `users` (deleted_at) و حذف سخت زمان‌بندی‌شده (DEC-112)؛ داده سلامت با cascade منطقی توسط job حذف.
- جداول `safety_decisions`، `audit_logs`، `authentication_events`، `safety_rule_versions`(پس از انتشار)، `workout_plan_versions` **append-only** (trigger/سرویس).
- فیلدهای متنی آزاد سلامت: رمزنگاری سطح اپلیکیشن (`*_enc`) یا کلید Secret Manager؛ توضیح در DOC-15.
- Enumها در Postgres به‌صورت `CHECK` یا `ENUM` (تصمیم پیاده‌سازی: Django `TextChoices` + CHECK constraint برای قابلیت migration).
- جزئیات هر فیلد: DOC-06.

## ۱. نمودار روابط (Mermaid)
```mermaid
erDiagram
""")
seen=set()
for (t,col,tt,tc,nul,ispk) in rels:
    key=(t,tt)
    card="||--o{" if nul=='N' and not ispk else "|o--o{"
    if ispk: card="||--||"
    if key in seen: continue
    seen.add(key)
    o+=f"    {tt} {card} {t} : \"{col}\"\n"
o+="```\n\n## ۲. فهرست موجودیت‌ها\n| ENT | جدول | ماژول | شرح |\n|---|---|---|---|\n"
for e in E: o+=f"| {e['ent']} | `{e['table']}` | {e['module']} | {e['desc']} |\n"
o+="\n## ۳. روابط (Cardinality، کلید خارجی، حذف)\n| از (فرزند) | ستون | به (والد) | Cardinality | Null | on delete |\n|---|---|---|---|---|---|\n"
for (t,col,tt,tc,nul,ispk) in rels:
    card="1:1" if ispk else "N:1"
    if t in('audit_logs','authentication_events','safety_decisions','red_flag_events'): od="RESTRICT (append-only؛ ناشناس‌سازی کاربر هنگام حذف)"
    elif tt=='users': od="RESTRICT + job حذف سخت (DEC-112)"
    elif t.startswith('exercise_') or t.startswith('workout_'): od="CASCADE در والد مالکیتی، در غیر این صورت RESTRICT"
    else: od="RESTRICT"
    o+=f"| `{t}` | `{col}` | `{tt}.{tc}` | {card} | {'Y' if nul=='Y' else 'N'} | {od} |\n"
o+="\n## ۴. محدودیت‌های جدول‌محور (Unique/Check)\n"
for e in E:
    if e['extra']:
        o+=f"- **`{e['table']}`**: "+"؛ ".join(e['extra'])+"\n"
o+="""
## ۵. ایندکس‌های اصلی (پیشنهاد اولیه؛ پس از بنچمارک تنظیم می‌شود)
- `users(lower(email))` UQ؛ `user_sessions(user_id, expires_at)`؛ `authentication_events(user_id, created_at)`.
- `health_conditions(user_id, status)`؛ `symptom_records(user_id, recorded_at desc)`؛ `pain_logs(user_id, recorded_at desc)`.
- `exercises(review_status, difficulty)`؛ `exercise_muscles(muscle_group_id)`؛ `exercise_equipment(equipment_id)`؛ `exercise_region_loads(region, loading)`؛ GIN روی `exercise_translations.synonyms` و trigram روی `name`.
- `workout_plan_versions(plan_id, version_no desc)`؛ `workout_sessions(user_id, started_at desc)`؛ `exercise_logs(session_id)` و `exercise_logs(client_uuid)` UQ.
- `safety_decisions(user_id, evaluated_at desc)`؛ `safety_rules(rule_set_version_id, stage)`.
- `audit_logs(subject_user_id, created_at desc)`؛ `outbox_events(status, created_at)`.

## ۶. جداول Deferred (از معماری حذف نشده‌اند؛ مشخصات در ورود به فاز)
"""
for k,v in DEFERRED.items(): o+=f"- **{k}**: "+"، ".join(f"`{x}`" for x in v)+"\n"
o+="""
## ۷. یکپارچگی بین ERD و سایر اسناد
- هر `workout_plan_versions.safety_decision_id` الزامی است ← PRI-001/AC-SAF-001.
- `features.safety_critical` + `plan_features` ← ADR-0003.
- `exercises.review_status='published'` فقط با `safety_tags_complete=true` ← SAF-R005.
- `exercise_logs.client_uuid` ← idempotency همگام‌سازی آفلاین (ADR-0004).
- بخش‌های `Pending Specialist Approval`: محتوای `safety_rules`(غیرساختاری)، `screening_responses.screening_version`، `medical_restrictions.max_loading`، جداول پروتکل.
"""
open('docs/02-architecture/05-DATABASE-ERD.md','w',encoding='utf-8').write(o)

# ---- Data dictionary ----
d=hdr("DOC-06","سند ۶ — Data Dictionary","""قالب ستون‌ها: فیلد | نوع | Nullable | Default | محدودیت | توضیح. `PK`=کلید اصلی، `UQ`=یکتا، `FK->t.c`=کلید خارجی، `CK`=قید بررسی.
""")
for m,ents in mods.items():
    d+=f"\n## ماژول `{m}`\n"
    for e in ents:
        d+=f"\n### {e['ent']} — `{e['table']}`\n{e['desc']}\n\n| فیلد | نوع | Nullable | Default | محدودیت | توضیح |\n|---|---|---|---|---|---|\n"
        for f in e['fields']:
            n,t,nl,df,c,ds=f.split('|')
            t=t.replace('|','\\|')
            d+=f"| `{n}` | `{t}` | {'بله' if nl=='Y' else 'خیر'} | {('`'+df+'`') if df else '—'} | {c or '—'} | {ds} |\n"
        if e['extra']: d+="\nمحدودیت‌های جدول: "+"؛ ".join(e['extra'])+"\n"
d+="\n## جداول Deferred\n"+"\n".join(f"- {k}: "+"، ".join(v) for k,v in DEFERRED.items())+"\n"
open('docs/02-architecture/06-DATA-DICTIONARY.md','w',encoding='utf-8').write(d)
print(len(E),"entities;",len(rels),"relationships")

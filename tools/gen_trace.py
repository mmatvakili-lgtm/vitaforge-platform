import re,json,collections
D='docs/'
prd=open(D+'01-product/01-PRD.md',encoding='utf-8').read()
us=open(D+'01-product/02-USER-STORIES.md',encoding='utf-8').read()
fr={}
for m in re.finditer(r'^\| (FR-[A-Z0-9]+-\d{3}) \| (.*?) \| (P[012])(?: \|(?: ([^|]*?) \|)?)?',prd,re.M):
    fr[m.group(1)]=dict(text=m.group(2).strip(),prio=m.group(3),phase=(m.group(4) or '').strip())
def expand(line):
    out=set()
    for m in re.finditer(r'FR-([A-Z0-9]+)-(\d{3})((?:\s*(?:\.\.|[،,])\s*(?:FR-[A-Z0-9]+-)?\d{3})*)',line):
        pre=m.group(1); a=int(m.group(2)); out.add(f"FR-{pre}-{a:03d}")
        for r in re.finditer(r'(\.\.|[،,])\s*(?:FR-([A-Z0-9]+)-)?(\d{3})',m.group(3)):
            p2=r.group(2) or pre; n=int(r.group(3))
            if r.group(1)=='..' : 
                for k in range(a,n+1): out.add(f"FR-{p2}-{k:03d}")
            else: out.add(f"FR-{p2}-{n:03d}")
    return out
stories={}
for blk in re.split(r'\n(?=\*\*US-)',us):
    m=re.match(r'\*\*(US-[A-Z0-9]+-\d{3})\*\* — (.*?)\.? \|(.*)',blk.split('\n')[0])
    if not m: continue
    head=blk.split('\n')[0]
    frs=expand(head)
    tst=re.findall(r'TST-[A-Z0-9]+-\d{3}(?:\.\.\d{3})?',head)
    pr=re.search(r'\| (P[012][^|]*?) \|',head)
    status='Deferred' if 'Deferred' in head else 'Not Started'
    stories[m.group(1)]=dict(title=m.group(2),frs=frs,tst=tst,status=status)
# mapping by FR prefix: (modules, pages, apis, entities, logic)
MAP={
"ACC":("MOD-IAM",["PG-AUTH-001..004"],["API-AUTH-001..008"],["users","user_roles","user_sessions","authentication_events"],"SVC-IdentityService"),
"PRIV":("MOD-AUD",["PG-PRIV-001","PG-ONB-001"],["API-PRIV-001..005"],["consent_documents","user_consents","data_requests","audit_logs"],"SVC-ConsentService, SVC-DataRightsService"),
"PRO":("MOD-PRO",["PG-PRO-001"],["API-PRO-001/002"],["user_profiles","user_preferences"],"SVC-ProfileService"),
"ONB":("MOD-ONB",["PG-ONB-001"],["API-ONB-001..003"],["assessments","assessment_answers","user_goals","training_profiles","availability_schedules","equipment_inventory"],"SVC-OnboardingService"),
"BODY":("MOD-BODY",["PG-BODY-001"],["API-BODY-001/002"],["body_measurements"],"SVC-BodyMetricsService"),
"HEALTH":("MOD-HEALTH",["PG-HEALTH-001"],["API-HEALTH-001..007"],["health_conditions","symptom_records","pain_logs","screening_responses","medical_restrictions","professional_clearances","out_of_scope_flags"],"SVC-HealthService"),
"SAFE":("MOD-SAFETY",["PG-HEALTH-001","PG-WO-001","PG-WO-002","PG-EX-002"],["API-HEALTH-006","API-EX-003","API-WO-001"],["safety_rule_versions","safety_rules","safety_decisions","red_flag_events"],"safety_core.engine"),
"EX":("MOD-EX",["PG-EX-001","PG-EX-002","PG-ADM-001"],["API-EX-001..003","API-ADM-001..003"],["exercises","exercise_translations","exercise_muscles","exercise_equipment","exercise_region_loads","exercise_cautions","exercise_contraindications","exercise_alternatives","exercise_media","exercise_sources","exercise_review_events"],"SVC-ExerciseCatalogService"),
"WO":("MOD-WO",["PG-WO-001"],["API-WO-001..004"],["workout_plans","workout_plan_versions","workout_phases","workout_days","workout_exercises","workout_sets","plan_change_events"],"workout_engine.planner"),
"LOG":("MOD-LOG",["PG-WO-002","PG-LOG-001"],["API-LOG-001..004"],["workout_sessions","exercise_logs","personal_records"],"SVC-WorkoutLogService"),
"PROG":("MOD-ANL",["PG-PROG-001","PG-DASH-001"],["API-PROG-001/002","API-DASH-001"],["workout_sessions","exercise_logs"],"SVC-ProgressService"),
"REC":("MOD-REC (Deferred)",[],[],["daily_checkins (Deferred)"],"Deferred"),
"NUT":("MOD-NUT (Deferred)",[],[],["Deferred"],"Deferred"),"FOOD":("MOD-NUT (Deferred)",[],[],["Deferred"],"Deferred"),"BUD":("MOD-NUT (Deferred)",[],[],["Deferred"],"Deferred"),"SUP":("MOD-NUT (Deferred)",[],[],["Deferred"],"Deferred"),
"AI":("MOD-AI",["PG-AI-001"],["API-AI-001"],["ai_conversations","ai_messages","prompt_versions","ai_model_versions","ai_usage"],"ai_gateway.pipeline"),
"SUB":("MOD-SUB",["PG-PUB-002","PG-SUB-001","PG-ADM-004"],["API-SUB-001..004","API-ADM-008"],["features","subscription_plans","plan_features","plan_quotas","subscriptions"],"SVC-EntitlementService"),
"I18N":("MOD-I18N",["همه صفحات"],["—"],["translations","user_profiles"],"frontend i18n + SVC-LocalizationService"),
"ADM":("MOD-ADM",["PG-ADM-001..004"],["API-ADM-001..008"],["user_roles","health_data_access_grants","safety_rule_versions"],"SVC-AdminService"),
"PRF":("MOD-PRF (Deferred)",[],[],["Deferred"],"Deferred"),
"CAL":("Deferred",[],[],[],"Deferred"),"DEV":("Deferred",[],[],[],"Deferred"),"VIS":("Deferred",[],[],[],"Deferred"),"COM":("Deferred",[],[],[],"Deferred"),
}
cov=collections.defaultdict(list)
for sid,s in stories.items():
    for f in s['frs']: cov[f].append(sid)
rows=[];unc=[]
for f,v in sorted(fr.items()):
    pre=f.split('-')[1]; mp=MAP.get(pre)
    deferred = v['prio']=='P2' or (mp and 'Deferred' in mp[0])
    sids=cov.get(f,[])
    tsts=sorted({t for s in sids for t in stories[s]['tst']})
    if not sids and not deferred: unc.append(f)
    status='Deferred' if deferred else ('Not Started' if sids else 'UNCOVERED')
    rows.append((f,v,sids,mp,tsts,status))
o="""# سند ۱۹ — Requirements Traceability Matrix

| فیلد | مقدار |
|---|---|
| Document ID | DOC-19 |
| Version | 0.1 |
| Status | Draft — تولیدشده خودکار توسط `tools/gen_trace.py`؛ پوشش P0/P1 بررسی‌شده |
| Created / Updated | 2026-11-07 |
| Owner | QA Lead / Architect |
| Related Documents | DOC-01، DOC-02، DOC-03، DOC-05، DOC-07، DOC-14، DOC-16 |

زنجیره: **Requirement → User Story → UI (PG) → API → Entity → Business Logic → Test**.
وضعیت واقعی پیاده‌سازی در ستون «وضعیت»: `Not Started` تا Milestone مربوط (به‌روزرسانی در IMPLEMENTATION_PLAN)، `Deferred` برای Backlog.
شناسه تست `TST-*` در ستون «Test» **شناسه رزرو‌شده** است؛ تا اجرای واقعی تست‌ها، نتیجه «Not Run» است.

| FR | اولویت/فاز | شرح | US | PG | API | Entity | Logic | Test (رزرو) | وضعیت |
|---|---|---|---|---|---|---|---|---|---|
"""
for f,v,sids,mp,tsts,status in rows:
    mp=mp or ("—",[],[],[],"—")
    o+=f"| {f} | {v['prio']}{(' / '+v['phase']) if v['phase'] else ''} | {v['text'][:70]}{'…' if len(v['text'])>70 else ''} | {', '.join(sids) or '—'} | {', '.join(mp[1]) or '—'} | {', '.join(mp[2]) or '—'} | {', '.join(mp[3][:4])}{'…' if len(mp[3])>4 else ''} | {mp[4]} | {', '.join(tsts) or '—'} | {status} |\n"
tot=len(rows); d=sum(1 for r in rows if r[5]=='Deferred'); c=sum(1 for r in rows if r[5]=='Not Started'); 
o+=f"""
## خلاصه پوشش
- کل FR: {tot}؛ دارای US (غیر Deferred): {c}؛ Deferred: {d}؛ **بدون پوشش (P0/P1): {len(unc)}** {unc if unc else ''}
- US ها: {len(stories)}
- هر API (DOC-07) در ستون API یا Deferred مرتبط است؛ بررسی خودکار: `tools/check_api_trace.py`.

## NFR/Safety Acceptance → تست
| معیار | تست/کنترل | سند |
|---|---|---|
| AC-SAF-001..006 | tests/architecture + safety suite | DOC-09 |
| AC-ARCH-001..005 | import-linter + AST | DOC-03 |
| AC-SEC-001..009 | permission matrix + scans | DOC-15 |
| AC-WO-001..007 | workout_engine tests | DOC-11 |
| AC-EX-001..005 | exercise catalog tests | DOC-10 |
| AC-AI-001..006 | ai_gateway tests | DOC-08 |
| AC-UI-001..005 | Playwright | DOC-14 |
| AC-DS-001..004 | lint + a11y | DOC-13 |
| AC-OPS-001..004 | CI | DOC-17 |
"""
open(D+'01-product/19-TRACEABILITY-MATRIX.md','w',encoding='utf-8').write(o)
print(tot,"FR",len(stories),"US","uncovered:",unc)
# API coverage check
api=json.load(open('tools/api_index.json'))
ui=open(D+'05-design/14-PAGE-BY-PAGE-UI.md',encoding='utf-8').read()
mm=[a[0] for a in api if a[0] not in ui and a[0].replace('API-','').split('-')[0] not in ('SYS',)]
import re as _r
def used(aid):
    # check "API-XXX-001..00N" style ranges or direct
    pre,mod,n=aid.split('-'); n=int(n)
    for m in _r.finditer(rf'API-{mod}-(\d{{3}})(?:\.\.(\d{{3}})|/(\d{{3}}))?',ui):
        a=int(m.group(1)); b=int(m.group(2)) if m.group(2) else (int(m.group(3)) if m.group(3) else a)
        if a<=n<=b or n in (a,b): return True
    return False
print("APIs not referenced in UI doc:",[a[0] for a in api if not used(a[0]) and not a[0].startswith('API-SYS')])

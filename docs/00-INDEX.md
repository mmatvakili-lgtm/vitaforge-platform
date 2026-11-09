<div dir="rtl">

# فهرست مرکزی مستندات — AI Fitness & Health Ecosystem

| فیلد | مقدار |
|---|---|
| Document ID | DOC-00 |
| Version | 0.3 |
| Status | Active |
| Created / Updated | 2026-11-07 |
| Owner | Product Owner |
| Related Decisions | DEC-001..132 (DOC-20) |

فاز: Phase 0 — مستندات اصلی ۲۰/۲۰ تولید شده‌اند. «Complete» یعنی **محتوای فنی کامل برای دامنه MVP**، نه تأیید بالینی/حقوقی. هر مورد Pending مشخص شده است.

## ساختار پوشه
```
docs/
├── 00-INDEX.md  README.md  CHANGELOG.md  OPEN_DECISIONS.md  MVP_SCOPE.md  IMPLEMENTATION_PLAN.md
├── 01-product/      01-PRD  02-USER-STORIES  19-TRACEABILITY-MATRIX
├── 02-architecture/ 03-SOFTWARE-ARCHITECTURE  04-ADR-REGISTER  04-adr/  05-DATABASE-ERD  06-DATA-DICTIONARY  07-OPENAPI-SPECIFICATION.yaml
├── 03-ai-safety/    08-AI-ARCHITECTURE  09-safety-clinical-governance
├── 04-domain/       10-EXERCISE-DATABASE  11-WORKOUT-ENGINE  12-NUTRITION-ENGINE
├── 05-design/       13-UI-UX-DESIGN-SYSTEM  14-PAGE-BY-PAGE-UI
├── 06-quality-ops/  15-SECURITY-PRIVACY  16-TESTING-STRATEGY  17-DEPLOYMENT-DEVOPS
├── 07-planning/     18-ROADMAP  20-assumptions-risks-decisions
├── references/      README.md (هیچ منبعی هنوز ثبت نشده)
└── tools/           schema_def.py gen_*.py (تولید ERD/DD/OpenAPI/Trace)
```

## قرارداد شناسه‌ها
FR-<MOD>-nnn، NFR-، SAF-، ST-، US-، AC-، TST-، ADR-nnnn، DEC-، ASM-، RSK-، EXP-، CON-، OPEN-، MOD-، ENT-، API-، PG-.

## وضعیت اسناد
| # | سند | نسخه | وضعیت | فایل |
|---|---|---|---|---|
| 1 | PRD | 0.2 | Complete (Draft v0.2) | `01-product/01-PRD.md` |
| 2 | User Stories & AC | 0.1 | Draft — Complete برای MVP | `01-product/02-USER-STORIES.md` |
| 3 | Software Architecture | 0.1 | Draft — Complete | `02-architecture/03-SOFTWARE-ARCHITECTURE.md` |
| 4 | ADR Register | 0.2 | Complete | `02-architecture/04-ADR-REGISTER.md` |
| 5 | Database ERD | 0.1 | Draft — Complete (MVP) | `02-architecture/05-DATABASE-ERD.md` |
| 6 | Data Dictionary | 0.1 | Draft — Complete (MVP) | `02-architecture/06-DATA-DICTIONARY.md` |
| 7 | OpenAPI Specification | 0.1.0 | Draft — Complete (MVP) | `02-architecture/07-OPENAPI-SPECIFICATION.yaml` |
| 8 | AI Architecture | 0.1 | Draft — LLM: Blocked (OPEN-002) | `03-ai-safety/08-AI-ARCHITECTURE.md` |
| 9 | Safety & Clinical Governance | 0.2 | Draft — `Pending Specialist Approval` (محتوای بالینی) | `03-ai-safety/09-safety-clinical-governance.md` |
| 10 | Exercise Database | 0.1 | Draft — ساختار Complete؛ محتوا `Pending Specialist Approval` | `04-domain/10-EXERCISE-DATABASE.md` |
| 11 | Workout Engine | 0.1 | Draft — پارامترها Unverified (EXP-013) | `04-domain/11-WORKOUT-ENGINE.md` |
| 12 | Nutrition Engine | 0.1 | Draft — Deferred Phase 3 | `04-domain/12-NUTRITION-ENGINE.md` |
| 13 | UI/UX Design System | 0.1 | Draft — Complete | `05-design/13-UI-UX-DESIGN-SYSTEM.md` |
| 14 | Page-by-Page UI | 0.1 | Draft — Complete (MVP) | `05-design/14-PAGE-BY-PAGE-UI.md` |
| 15 | Security & Privacy | 0.1 | Draft — Pending Legal Review | `06-quality-ops/15-SECURITY-PRIVACY.md` |
| 16 | Testing Strategy | 0.1 | Draft — Complete | `06-quality-ops/16-TESTING-STRATEGY.md` |
| 17 | Deployment & DevOps | 0.1 | Draft — Not Run | `06-quality-ops/17-DEPLOYMENT-DEVOPS.md` |
| 18 | Roadmap | 0.1 | Draft — Complete | `07-planning/18-ROADMAP.md` |
| 19 | Traceability Matrix | 0.1 | Draft — خودکار؛ بدون FR بدون پوشش | `01-product/19-TRACEABILITY-MATRIX.md` |
| 20 | Assumptions, Risks & Decisions | 0.2 | Complete | `07-planning/20-assumptions-risks-decisions.md` |
| — | OPEN_DECISIONS | 0.1 | Active (OPEN-001..007) | `OPEN_DECISIONS.md` |
| — | MVP_SCOPE / IMPLEMENTATION_PLAN / CHANGELOG / README | 0.1 | Active | ریشه docs |

## گزارش سازگاری (۲۰۲۶-۱۱-۰۷)
- ERD ↔ Data Dictionary: تولید از منبع واحد `schema_def.py` (۶۷ موجودیت؛ همه FK معتبر؛ Mermaid با mmdc رندر شد).
- OpenAPI: ۵۶ endpoint؛ همه `$ref` معتبر؛ هر API در UI Spec ارجاع دارد.
- Traceability: ۱۱۲ FR؛ هیچ FR با اولویت P0/P1 بدون User Story نیست.
- Safety ↔ Workout Engine: `SafetyDecision` پیش‌شرط تولید برنامه (DOC-11 S1/S7 ↔ DOC-09 §5، DOC-05 `workout_plan_versions.safety_decision_id`).
- AI ↔ Safety: Validator + `external_health_data=false` (DOC-08 §4/§6).
- بسته‌شده: CON-001، 002، 004، 008 (کامل)، CON-005 (طراحی؛ محتوا Pending)، CON-006/007 (ERD/API تولید شد).
- **بررسی‌نشده:** اعتبارسنجی رسمی OpenAPI با validator خارجی (ابزار نصب نیست)؛ بازبینی انسانی/بالینی/حقوقی؛ هیچ منبع خارجی ثبت نشده.

- سند‌های تکمیلی: `DECISION_REGISTRY.md`، `CAPABILITY_STATUS.md`، `RELEASE_CHECKLIST.md`، `MVP_GAP_ANALYSIS.md`، `CONTRACT_REPORT.md`، `DJANGO_RUNTIME_VALIDATION.md`، `EXERCISE_CATALOG_SECURITY.md`، `API_GAPS.md`، `LANGUAGE_POLICY.md`، `04-domain/10A-DATA-ACQUISITION.md`، `04-domain/12A-NUTRITION-API-ADDENDUM.md`.

</div>

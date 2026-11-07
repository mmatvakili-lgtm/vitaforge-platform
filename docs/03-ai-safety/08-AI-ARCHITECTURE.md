<div dir="rtl">

# سند ۸ — `AI Architecture Specification`

| فیلد | مقدار |
|---|---|
| Document ID | DOC-08 |
| Version | 0.1 |
| Status | Draft — Complete (طراحی)؛ LLM واقعی: Deferred/Blocked تا OPEN-002 |
| Created / Updated | 2026-11-07 |
| Owner | AI Engineer |
| Related Documents | DOC-03، DOC-09، DOC-15، DOC-07 (API-AI-001) |
| Related Decisions | DEC-007، 105، 123، 129، 131؛ ADR-0002، ADR-0005؛ EXP-012 |

## 1. اصول
1. AI هرگز تصمیم ایمنی نمی‌گیرد؛ هر خروجی از Safety Core و Validator می‌گذرد.
2. **برنامه‌سازی در MVP کاملاً قاعده‌محور است؛ LLM فقط برای توضیح/آموزش (اختیاری، پشت Flag).**
3. با قطع AI: Safety Core، برنامه‌سازی و UI کامل کار می‌کنند (`mode=rule_based_fallback`).
4. `external_health_data=false` ثابت: هیچ داده سلامت (حتی Redact‌شده) به Provider خارجی نمی‌رود تا EXP-012.
5. Provider-agnostic؛ هزینه، تأخیر و سقف مصرف قابل‌اندازه‌گیری.
6. ادعای علمی بدون منبع تأییدشده ممنوع؛ عدم قطعیت صریح.

## 2. مسیر درخواست (Pipeline اجباری ۹ مرحله‌ای سند مادر)
```
1 Intent classify (rule-based؛ بدون LLM) ─ explain_plan | technique | general | unsafe/medical
2 Authorized context (ContextBuilder): فقط فیلدهای مجاز طبق Purpose Policy
3 Warning check  ─┐
4 Constraint check├─ SafetyGate.evaluate (Safety Core) → اگر STOP/BLOCK → پاسخ ثابت قالب‌دار، بدون LLM
5 Evidence retrieval: KnowledgeBase (kb_chunks فقط published؛ Phase 4)
6 Deterministic computation (محاسبات/ارجاع داده‌ها در سرور، نه در LLM)
7 Generation: ModelGateway.generate(prompt_version, structured schema)
8 Validation: OutputValidator (schema + ایمنی + منبع + ممنوعیت‌ها)
9 Present: متن + منابع + سطح عدم قطعیت + decision_id
```
خطا یا رد در هر مرحله ← fallback قالب‌دار + ثبت لاگ.

## 3. اجزا
| جزء | مسئولیت |
|---|---|
| `IntentRouter` | قاعده/کلیدواژه + فهرست سفید purposeها؛ درخواست تشخیص/درمان/دوز → پاسخ ثابت «خارج از حوزه» + ارجاع |
| `ContextBuilder` + `PurposePolicy` | هر Purpose فهرست سفید فیلد دارد (مثلاً explain_plan: ساختار برنامه، نام حرکات، دلیل‌ها؛ **بدون** درد، تشخیص، تاریخ تولد، نام) |
| `Redactor` | حذف/شبه‌ناشناس‌سازی PII؛ تست property-based که هیچ فیلد سلامت از مرز عبور نمی‌کند |
| `SafetyGate` (Port) | همان Safety Core؛ ورودی/خروجی DOC-09 |
| `KnowledgeBase` + `VectorStore` | RAG روی محتوای published با منبع؛ pgvector (ADR-0005)؛ Phase 4 |
| `ModelGateway` + `LLMProvider` | `generate(request) → ModelResponse`؛ Adapterها: `StubProvider` (dev/test)، `SelfHostedProvider`، `ExternalProvider`(غیرفعال برای سلامت) |
| `PromptRegistry` | `prompt_versions` نسخه‌دار با `output_schema`؛ تغییر = نسخه جدید + ارزیابی |
| `OutputValidator` | (۱) JSON-schema (۲) فهرست ممنوع (تشخیص، وعده درمان، دوز مکمل، تشویق به تحمل درد) (۳) هر نام حرکت ∈ مجموعه مجاز SafetyDecision (SAF-R009) (۴) استناد به منبع الزامی برای ادعای علمی (۵) نرمال‌سازی عدم قطعیت |
| `QuotaService` | `plan_quotas` + `ai_usage`؛ 402 در اتمام سهمیه (غیر ایمنی) |
| `AuditLogger` | `ai_messages` با `content_redacted`، نسخه prompt/model، `safety_decision_id` |
| `EvalHarness` | مجموعه ارزیابی (Groundedness، `Safety Violation Rate`، Format)، اجرای CI روی Stub |

## 4. Provider Abstraction
```
class LLMProvider(Protocol):
    code: str
    external: bool
    def generate(self, req: ModelRequest) -> ModelResponse: ...
```
- `ModelRequest`: prompt_id/version، messages، `output_schema`، `max_tokens`، `timeout`، `data_class` (`non_health` | `health_redacted`).
- Gateway قاعده سخت: اگر `provider.external and data_class != 'non_health'` ← `PolicyViolation` (قابل تغییر فقط با ADR + EXP-012).
- Timeout/Retry (backoff محدود)، Circuit breaker، Fallback به قالب ثابت.
- تعویض Provider: فقط پیکربندی `AI_PROVIDER` و رکورد `ai_model_versions`.

## 5. مدیریت Prompt
- ساختار: system policy ثابت (ممنوعیت‌ها) + task template + context blocks با delimiter؛ ورودی کاربر هرگز در system.
- دفاع در برابر Prompt Injection: ورودی کاربر داده است نه دستور؛ خروجی صرفاً از طریق Validator؛ LLM ابزار/دسترسی DB ندارد (MVP: بدون tool calls).
- نسخه‌بندی و Approved status؛ prompt `draft` در Production بارگذاری نمی‌شود.

## 6. سیاست داده و حریم
| داده | به LLM خارجی | به LLM داخلی/خودی | لاگ |
|---|---|---|---|
| داده سلامت/درد/تشخیص | **هرگز** | فقط با Purpose مجاز + رضایت (Phase 4+) | فقط Redacted |
| ساختار برنامه/نام حرکات | با Redaction مجاز (پس از تأیید حقوقی) | مجاز | Redacted |
| متن کاربر آزاد | اسکن PII/سلامت؛ در صورت وجود → رد یا پاسخ ثابت | محدود | Redacted |

## 7. ارزیابی و معیارها
Groundedness، Accuracy (روی مجموعه طلایی تأییدشده)، `Safety Violation Rate` (هدف: ۰ روی مجموعه منفی)، Refusal correctness، latency p95، هزینه/تعامل، نرخ پذیرش. مجموعه‌های ارزیابی بالینی: `Pending Specialist Approval`.

## 8. حالت‌های خطا
| وضعیت | رفتار |
|---|---|
| Provider down/timeout | `mode=rule_based_fallback`؛ 503 فقط برای قابلیت‌هایی که وابسته‌اند |
| Validator reject | پاسخ ثابت + ثبت Safety event |
| سهمیه تمام | 402 (غیر ایمنی) |
| Safety STOP | پاسخ قالب‌دار ایمنی (رایگان، بدون سهمیه) |
| درخواست تشخیص/دوز | پاسخ ثابت + ارجاع |

## 9. RAG (Phase 4؛ Deferred)
`kb_documents/kb_chunks`: فقط `published` و دارای `scientific_sources`؛ embedding با Provider داخلی؛ بازیابی top-k با فیلتر زبان/محدوده کاربرد؛ هر پاسخ منبع‌دار؛ اگر بازیابی ضعیف (آستانه پیکربندی) ← «اطلاعات کافی نیست». معیار ارزیابی pgvector در ADR-0005.

## 10. معیارهای پذیرش
| ID | معیار |
|---|---|
| AC-AI-001 | با Provider=Stub همه مراحل Pipeline تست شوند |
| AC-AI-002 | تلاش ارسال health داده به Provider خارجی → PolicyViolation (تست) |
| AC-AI-003 | قطع Provider ← fallback و Safety Core فعال |
| AC-AI-004 | خروجی با نام حرکت خارج از مجموعه مجاز ← رد |
| AC-AI-005 | پرامپت‌های prompt-injection نمونه ← بدون نشت/نقض (مجموعه تست) |
| AC-AI-006 | لاگ‌ها فاقد PII/سلامت (تست اسکن) |

</div>

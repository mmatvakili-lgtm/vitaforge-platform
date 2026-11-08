"""Human-readable explanations for every reason code (DOC-09 S6). Pure data + formatting; no clinical claims."""
from __future__ import annotations

from typing import Dict, List

from .models import SafetyDecision

TEXT: Dict[str, Dict[str, str]] = {
    "SAF-R001": {"fa": "کاربر زیر ۱۸ سال است؛ این برنامه فقط برای بزرگسالان است.", "en": "User is under 18; adults only."},
    "SAF-R002": {"fa": "رضایت پردازش داده سلامت معتبر نیست.", "en": "Health-data consent is not valid."},
    "SAF-R003": {"fa": "اطلاعات لازم کامل نیست؛ به پرسش‌های زیر پاسخ بده.", "en": "Required information is missing; please answer the questions."},
    "SAF-R004": {"fa": "خطای داخلی؛ برای ایمنی هیچ برنامه‌ای ساخته نشد.", "en": "Internal error; no plan was produced for safety."},
    "SAF-R005": {"fa": "حرکت بازبینی/برچسب‌گذاری ایمنی کامل ندارد.", "en": "Exercise is not reviewed or lacks complete safety tags."},
    "SAF-R006": {"fa": "برای ناحیه ثبت‌شده شما منع یا احتیاط دارد.", "en": "Exercise has a contraindication for a recorded region."},
    "SAF-R007": {"fa": "محدودیت ثبت‌شده قابل تحلیل نیست؛ آن ناحیه کاملاً محدود شد.", "en": "A recorded restriction could not be analysed; the region was fully restricted."},
    "SAF-R008": {"fa": "بارداری در دامنه این برنامه نیست؛ با متخصص مشورت کن.", "en": "Pregnancy is out of scope; consult a professional."},
    "SAF-R011": {"fa": "برای درد جدید/نامشخص برنامه‌ای ساخته نمی‌شود؛ ارجاع به متخصص.", "en": "No program is built for new/unclear pain; referral advised."},
    "SAF-R013": {"fa": "محتوای بالینی هنوز بازبینی تخصصی نشده است.", "en": "Clinical content has not been expert reviewed."},
    "SAF-R014": {"fa": "محدودیت ثبت‌شده منقضی شده؛ همچنان اعمال می‌شود و بازبینی لازم است.", "en": "A restriction has expired; still applied, reassessment recommended."},
    "SAF-R015": {"fa": "هیچ حرکت مجازی باقی نماند.", "en": "No valid exercise remains."},
    "SAF-R016": {"fa": "مسیر بازتوانی/آسیب تشخیص‌داده‌شده فعلاً پشتیبانی نمی‌شود؛ ارجاع.", "en": "Diagnosed-injury pathway is not supported yet; referral."},
    "SAF-R017": {"fa": "شرایط شما خارج از دامنه این برنامه است.", "en": "Your situation is outside this app's scope."},
    "SAF-R018": {"fa": "قاعده ایمنی نامعتبر؛ برای ایمنی متوقف شد.", "en": "Invalid safety rule; stopped for safety."},
    "SAF-R019": {"fa": "تجهیزات لازم برای این حرکت در اختیار شما نیست.", "en": "You do not have the equipment this exercise needs."},
    "SAF-R020": {"fa": "سطح دشواری حرکت بالاتر از سطح فعلی شماست.", "en": "Exercise difficulty is above your current level."},
    "SAF-R100": {"fa": "علامت هشدار گزارش شد؛ لطفاً قبل از تمرین با متخصص/پزشک مشورت کن.", "en": "A warning sign was reported; please consult a professional before training."},
    "SAF-R101": {"fa": "وضعیت ثبت‌شده شما نیاز به ارجاع فوری دارد.", "en": "Your recorded status needs urgent referral."},
    "SAF-R102": {"fa": "درد در حال بدتر شدن است؛ ارجاع به متخصص.", "en": "Pain is getting worse; referral advised."},
    "SAF-R300": {"fa": "با محدودیت ثبت‌شده برای این ناحیه سازگار نیست.", "en": "Not compatible with the recorded restriction for this region."},
    "SAF-R301": {"fa": "ناحیه احتیاط (خوداظهاری): بار این حرکت بیشتر از حد مجاز احتیاطی است.", "en": "Caution region (self-reported): this exercise loads it more than the cautious limit."},
    "SAF-R302": {"fa": "این ناحیه نیاز به ارزیابی مجدد دارد؛ فعلاً محدود شد.", "en": "This region needs reassessment; temporarily restricted."},
}
UNKNOWN = {"fa": "دلیل ثبت‌نشده (کد ناشناخته).", "en": "Unrecognised reason code."}


def explain(decision: SafetyDecision, lang: str = "fa") -> Dict[str, object]:
    """Explain why the overall decision and each exercise was allowed / limited / rejected."""
    msg = lambda code: TEXT.get(code, UNKNOWN).get(lang, UNKNOWN["en"]) if code.startswith("SAF-") else code
    items: List[Dict[str, object]] = []
    for it in decision.per_item:
        state = "rejected" if not it.allowed else ("allowed_with_caution" if it.caution else "allowed")
        items.append({"code": it.code, "state": state, "why": [{"reason": r, "text": msg(r)} for r in it.reasons]})
    return {"decision_id": decision.decision_id, "status": decision.status.value, "rule_set_version": decision.rule_set_version,
            "overall": [{"reason": r, "text": msg(r)} for r in decision.reasons if r.startswith("SAF-")],
            "questions": list(decision.required_questions), "items": items, "flags": list(decision.flags)}

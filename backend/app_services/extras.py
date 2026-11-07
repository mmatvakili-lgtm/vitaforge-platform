"""Body measurements, pain logs, health profile view, dashboard/monthly progress, privacy export & erasure."""
from __future__ import annotations

import dataclasses
import hashlib

from .errors import NotFound, ValidationFailed

GUIDANCE_PAIN = {
    "fa": "درد فعال یا جدید نیازمند ارزیابی متخصص است. این برنامه برای درد برنامه درمانی نمی‌سازد؛ تا زمان بررسی، از حرکتی که درد را زیاد می‌کند خودداری کن و در صورت علائم هشدار فوراً به پزشک مراجعه کن.",
    "en": "Active or new pain needs a professional assessment. This app does not build treatment plans for pain; avoid movements that aggravate it and seek urgent care for warning signs.",
}


class ExtrasService:
    def __init__(self, store, health, workouts, today):
        self.s, self.h, self.w, self.today = store, health, workouts, today
        for k in ("measurements", "pain_logs", "erasure_audit"):
            self.s.__dict__.setdefault(k, {} if k != "erasure_audit" else [])

    def add_measurement(self, uid, weight_kg=None, height_cm=None):
        if weight_kg is None and height_cm is None:
            raise ValidationFailed("empty")
        if weight_kg is not None and not 20 <= weight_kg <= 400:
            raise ValidationFailed("weight")
        if height_cm is not None and not 80 <= height_cm <= 250:
            raise ValidationFailed("height")
        self.s.measurements.setdefault(uid, []).append({"day": self.today(), "weight_kg": weight_kg, "height_cm": height_cm})

    def body_overview(self, uid):
        rows = self.s.measurements.get(uid, [])
        last = next((r for r in reversed(rows) if r["weight_kg"] is not None), None)
        h = next((r["height_cm"] for r in reversed(rows) if r["height_cm"] is not None), None)
        bmi = round(last["weight_kg"] / (h / 100) ** 2, 1) if last and h else None
        return {"entries": len(rows), "latest_weight_kg": last["weight_kg"] if last else None, "bmi": bmi,
                "note": "BMI is informational only; not a diagnosis."}

    def log_pain(self, uid, region, intensity, during_session=None):
        if not isinstance(intensity, int) or not 0 <= intensity <= 10:
            raise ValidationFailed("intensity")
        self.h.add_condition(uid, region, "pain", "self_reported_symptom", "self_reported", active_pain=intensity > 0)  # re-evaluated by Safety Core
        self.s.pain_logs.setdefault(uid, []).append({"day": self.today(), "region": region, "intensity": intensity,
                                                     "session": during_session})
        return {"guidance": GUIDANCE_PAIN if intensity > 0 else None, "plan_will_be_reevaluated": True}

    def health_profile(self, uid):
        h = self.s.health.get(uid, {"conditions": [], "restrictions": [], "flags": [], "answers": {}})
        return {"conditions": [dataclasses.asdict(c) for c in h["conditions"]], "restrictions": [dataclasses.asdict(r) for r in h["restrictions"]],
                "out_of_scope": [f.flag_type for f in h["flags"] if f.active]}

    def monthly_progress(self, uid, month_start, month_end):
        return self.w.weekly_progress(uid, month_start, month_end)

    def dashboard(self, uid):
        t = self.today()
        plan = self.s.plans.get(uid)
        return {"week": self.w.weekly_progress(uid, t - 6, t), "has_plan": bool(plan), "plan_version": plan[-1]["version"] if plan else None,
                "plan_label": plan[-1]["result"].label if plan else None}

    # ---- privacy (FR-PRIV): export everything, erase on request
    def export(self, uid):
        u = self.s.users.get(uid)
        if not u:
            raise NotFound()
        return {"account": {k: v for k, v in u.items() if k not in ("pw",)}, "profile": self.s.profiles.get(uid),
                "health": self.health_profile(uid), "consents": [c for c in self.s.consents if c["user"] == uid],
                "measurements": self.s.measurements.get(uid, []), "pain_logs": self.s.pain_logs.get(uid, []),
                "plans": [{"version": v["version"], "cause": v["cause"], "codes": list(v["result"].codes)} for v in self.s.plans.get(uid, [])],
                "workout_sessions": [w for w in self.s.workout_sessions.values() if w["user"] == uid]}

    def erase(self, uid):
        u = self.s.users.pop(uid, None)
        if not u:
            raise NotFound()
        self.s.by_email.pop(u["email"], None)
        for k in ("profiles", "health", "plans", "measurements", "pain_logs"):
            getattr(self.s, k).pop(uid, None)
        self.s.sessions = {h: x for h, x in self.s.sessions.items() if x["user"] != uid}
        self.s.workout_sessions = {k: v for k, v in self.s.workout_sessions.items() if v["user"] != uid}
        self.s.consents = [c for c in self.s.consents if c["user"] != uid]
        self.s.erasure_audit.append({"user_hash": hashlib.sha256(uid.encode()).hexdigest()[:16], "day": self.today()})   # no PII kept

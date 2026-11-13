"""Plan generation (immutable versions), substitution, session logging, weekly progress."""
from __future__ import annotations

import dataclasses

from safety_core import SafetyCore
from workout_engine import EngineConfig, EngineInput, generate_plan

from .errors import Conflict, NeedsContent, Forbidden, NotFound, PreconditionRequired, SafetyBlocked, ValidationFailed


class WorkoutService:
    def __init__(self, store, health, gate: SafetyCore, clock_days, config: EngineConfig = EngineConfig(), clock_s=None):
        self.s, self.h, self.gate, self.today, self.cfg = store, health, gate, clock_days, config
        self.now = clock_s or (lambda: None)

    def generate(self, uid, preferred_structure="__profile__"):
        p = self.s.profiles.get(uid)
        if not p or not p.get("complete"):
            raise PreconditionRequired("onboarding")
        st = p["steps"]
        inp = EngineInput(uid, st["goal"]["goal"], st["goal"]["level"], st["schedule"]["days_per_week"],
                          st["schedule"]["session_minutes"], tuple(st["equipment"]["equipment"]),
                          tuple(c for c in self.s.catalog.values()
                                if not st["equipment"].get("environment") or not c.environments or st["equipment"]["environment"] in c.environments),
                          st["schedule"].get("preferred_structure") if preferred_structure == "__profile__" else preferred_structure, config=self.cfg)
        base = self.h.safety_request(uid)
        rs = self.gate.rule_set
        supportive = tuple(sorted({c.region for c in base.conditions if not c.active_pain and c.status != "no_known_limitation"}))
        inp = dataclasses.replace(inp, priority_muscles=tuple(st["goal"].get("priority_muscles", ())), supportive_regions=supportive,
                                  supportive_enabled=bool(rs.clinical_content_published or rs.allow_unreviewed_content))
        res = generate_plan(inp, base, self.gate)
        # the same pre-pass request the engine used (S1), so the returned decision is the one that gated the plan
        pre = self.gate.evaluate(dataclasses.replace(base, candidates=tuple(c.candidate for c in sorted(inp.catalog, key=lambda c: c.code)),
                                                    equipment=tuple(inp.equipment), user_level=inp.level))
        if res.status in ("BLOCKED", "ERROR_FAILSAFE"):
            raise SafetyBlocked(res.status, res.reasons, res.safety_decision_id, decision=pre)
        if res.status == "NEEDS_CONTENT":
            raise NeedsContent(res.reasons, [f"{o.day}:{o.slot}:{o.reason}" for o in res.omissions])
        if res.status != "OK":
            raise ValidationFailed(res.status + ":" + ",".join(res.reasons))
        versions = self.s.plans.setdefault(uid, [])
        versions.append({"version": len(versions) + 1, "result": res, "day": self.today(), "cause": "generate", "decision": pre, "ts": self.now()})
        return versions[-1]

    def current(self, uid):
        v = self.s.plans.get(uid)
        if not v:
            raise NotFound()
        return v[-1]

    def substitute(self, uid, code, reason):
        if reason not in ("pain", "equipment", "preference", "other"):
            raise ValidationFailed("reason")
        cur = self.current(uid)["result"]
        if code not in cur.codes:
            raise NotFound()
        cands = [c.candidate for c in self.s.catalog.values()]
        req = self.h.safety_request(uid, cands)
        catalog = {c.code: c.candidate for c in self.s.catalog.values()}
        alts = [a for a in self.gate.find_alternatives(code, self.s.relations, catalog, req) if a not in cur.codes]
        if not alts:
            return None                                    # "no valid alternative": never guess
        import dataclasses
        from workout_engine.models import PlannedDay
        new_days = []
        for d in cur.days:
            ex = tuple(dataclasses.replace(e, code=alts[0], reason="substitution") if e.code == code else e for e in d.exercises)
            new_days.append(PlannedDay(d.name, ex, d.estimated_minutes))
        new = dataclasses.replace(cur, days=tuple(new_days))
        ok, viol = self.gate.validate_plan(new.codes, self.gate.evaluate(req), req)
        if not ok:
            raise SafetyBlocked("ERROR_FAILSAFE", viol)
        versions = self.s.plans[uid]
        versions.append({"version": len(versions) + 1, "result": new, "day": self.today(), "cause": "substitute:" + reason,
                         "pain_log": reason == "pain", "decision": self.gate.evaluate(req), "ts": self.now()})
        return versions[-1]

    # ---- logging
    def start_session(self, uid, day_name, now=None):
        cur = self.current(uid)["result"]
        if day_name not in [d.name for d in cur.days]:
            raise NotFound()
        sid = self.s.new_id("wks")
        self.s.workout_sessions[sid] = {"id": sid, "user": uid, "day_name": day_name, "start": self.today(), "start_ts": now, "logs": [],
                                        "finished": False}
        return sid

    def log_set(self, uid, sid, code, reps, load_kg, rpe=None, client_uuid=None, set_no=None, skipped=False, duration_sec=None):
        """Idempotent on client_uuid: a retry returns the original entry (offline sync safe). Returns (entry, created, is_pr)."""
        ws = self._own(uid, sid)
        if client_uuid is not None:
            for l in ws["logs"]:
                if l.get("client_uuid") == client_uuid:
                    return l, False
        if ws["finished"]:
            raise Conflict("finished")
        if skipped:
            reps, load_kg = 0, 0
        elif duration_sec is not None and reps is None:
            reps = 0                                       # time-based set (e.g. plank): no reps, no PR logic
        if not (isinstance(reps, int) and (0 < reps <= 200 or skipped or duration_sec is not None)) or not (0 <= load_kg <= 1000) \
                or (rpe is not None and not 1 <= rpe <= 10):
            raise ValidationFailed("log")
        prev = [l["load_kg"] for w in self.s.workout_sessions.values() if w["user"] == uid for l in w["logs"]
                if l["code"] == code and l["reps"] > 0 and not l.get("skipped")]
        pr = bool(prev) and reps > 0 and not skipped and float(load_kg) > max(prev)     # strictly heavier than any earlier set; first set is a baseline, not a PR
        entry = {"code": code, "reps": reps, "load_kg": float(load_kg), "rpe": rpe, "client_uuid": client_uuid, "set_no": set_no,
                 "skipped": skipped, "duration_sec": duration_sec, "pr": pr}
        ws["logs"].append(entry)
        return entry, True

    def finish(self, uid, sid, now=None, perceived_difficulty=None, aborted_reason=None, notes=None, pain_region=None):
        ws = self._own(uid, sid)
        if ws["finished"]:
            raise Conflict("already_finished")
        ws.update(finished=True, end_ts=now, perceived_difficulty=perceived_difficulty, aborted_reason=aborted_reason, notes=notes, pain_region=pain_region if aborted_reason == "pain" else None)
        done = [l for l in ws["logs"] if not l.get("skipped")]
        dur = (now - ws["start_ts"]) // 60 if now is not None and ws.get("start_ts") is not None else None
        return {"volume_kg": sum(l["reps"] * l["load_kg"] for l in done), "sets_done": len(done), "duration_min": dur}

    def weekly_progress(self, uid, week_start, week_end):
        ss = [w for w in self.s.workout_sessions.values() if w["user"] == uid and w["finished"] and week_start <= w["start"] <= week_end]
        vol = sum(l["reps"] * l["load_kg"] for w in ss for l in w["logs"])
        return {"sessions": len(ss), "sets": sum(len(w["logs"]) for w in ss), "volume_kg": vol}

    def _own(self, uid, sid):
        ws = self.s.workout_sessions.get(sid)
        if not ws or ws["user"] != uid:
            raise NotFound()                               # no existence leak across users
        return ws

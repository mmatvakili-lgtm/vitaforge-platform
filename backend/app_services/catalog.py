"""Exercise catalog lifecycle (DOC-10 §lifecycle) and safety rule-set publication (DOC-09).

draft -> scientific_review -> safety_review -> published -> retired.
Publication needs a recorded reviewer sign-off by the right role; the system never self-approves.
"""
from __future__ import annotations

from exercise_catalog.schema import publication_blockers

from .errors import Forbidden, NotFound, ValidationFailed

FLOW = ["draft", "scientific_review", "safety_review", "published"]
ROLE_FOR_TARGET = {"scientific_review": "content_admin", "safety_review": "exercise_reviewer",
                   "published": "clinical_safety_reviewer"}


class CatalogService:
    def __init__(self, store):
        self.s = store
        self.s.__dict__.setdefault("exercise_meta", {})
        self.s.__dict__.setdefault("rule_sets", {})

    def create_draft(self, actor_role, code, candidate_factory, **meta):
        if actor_role not in ("content_admin", "admin"):
            raise Forbidden()
        if code in self.s.exercise_meta:
            raise ValidationFailed("duplicate")
        self.s.exercise_meta[code] = {"code": code, "status": "draft", "version": 1, "signoffs": [], "sample": bool(meta.get("sample")),
                                      "factory": candidate_factory, "tags_complete": bool(meta.get("tags_complete", False)),
                                      "record": meta.get("record")}
        return code

    def transition(self, actor_role, actor_id, code, target, tags_complete=False):
        if actor_role not in set(ROLE_FOR_TARGET.values()) | {"admin"}:
            raise Forbidden()                                      # authorise before revealing whether the code exists
        m = self.s.exercise_meta.get(code)
        if not m:
            raise NotFound()
        if target == "retired":
            if actor_role not in ("clinical_safety_reviewer", "admin"):
                raise Forbidden()
            m["status"] = "retired"
            self._sync(code)
            return m
        in_flow = target in FLOW and m["status"] in FLOW
        if not in_flow or FLOW.index(target) != FLOW.index(m["status"]) + 1:
            raise ValidationFailed("invalid_transition")
        if actor_role != ROLE_FOR_TARGET[target]:
            raise Forbidden()                                      # even `admin` cannot publish clinical content
        if target == "published":
            if not tags_complete:
                raise ValidationFailed("safety_tags_incomplete")
            if m["sample"]:
                raise ValidationFailed("sample_content_cannot_be_published")
            # Independent of lifecycle roles/sign-offs: the ExerciseRecord itself must carry approved review, reviewed tags, sources and
            # confirmed license. A role chain alone (or a self-declared `tags_complete`) is never enough.
            rec = m.get("record")
            if rec is None:
                raise ValidationFailed("no_exercise_record")
            if publication_blockers(rec):
                raise ValidationFailed("record_not_publishable")
        m["status"] = target
        m["signoffs"].append({"role": actor_role, "actor": actor_id, "to": target})
        self._sync(code)
        return m

    def _sync(self, code):
        """Only published exercises enter the engine catalog; others are removed at once."""
        m = self.s.exercise_meta[code]
        if m["status"] == "published":
            self.s.catalog[code] = m["factory"]()
        else:
            self.s.catalog.pop(code, None)

    # ---- user-facing: never returns non-published (AC-EX-003)
    def list_public(self):
        return sorted(self.s.catalog)

    def get_public(self, code):
        if code not in self.s.catalog:
            raise NotFound()
        return self.s.catalog[code]

    def coverage_report(self):
        pats = {}
        for c in self.s.catalog.values():
            pats[c.candidate.movement_pattern] = pats.get(c.candidate.movement_pattern, 0) + 1
        return pats

    # ---- rule sets
    def publish_rule_set(self, actor_role, actor_id, version, expert_signoff_ref):
        """Publishing clinical rules requires a recorded external expert approval reference (EXP-*)."""
        if actor_role != "clinical_safety_reviewer":
            raise Forbidden()
        if not expert_signoff_ref or not str(expert_signoff_ref).strip():
            raise ValidationFailed("expert_signoff_required")
        self.s.rule_sets[version] = {"status": "published", "by": actor_id, "ref": expert_signoff_ref}
        return self.s.rule_sets[version]

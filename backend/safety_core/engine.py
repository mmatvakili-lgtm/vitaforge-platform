"""Safety Core engine: deterministic, LLM-independent, fail-safe.

Evaluation priority (DOC-09 §5) stops at the first terminal match:
 1 input/consent/age -> 2 out-of-scope -> 3 red flags -> 4 urgent-referral status ->
 clinical-content gate -> 5 pathway B -> 6..9 per-item filters (restrictions, contraindications,
 caution regions, tag completeness).

Conservative defaults everywhere clinical content is undefined (EXP-001/002/003/011):
 * unknown/expired restrictions still restrict;
 * region loads must be present for ALL regions or the exercise is blocked;
 * unreviewed clinical content is only usable when RuleSet.allow_unreviewed_content (dev/test).
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from . import jsonlogic
from .errors import InvalidInput, RuleError
from .hashing import decision_id_from_hash, inputs_hash
from .models import (
    CONDITION_STATUSES, LOADING_RANK, LOADINGS, OUT_OF_SCOPE_TYPES, PROBLEM_TYPES, REGIONS, SOURCES,
    ClinicalRule, Condition, DecisionStatus, ExerciseCandidate, ItemResult, RuleSet, SafetyDecision,
    SafetyRequest,
)

# Reason codes (documented in DOC-09 §6.1 / §6.2)
R_AGE = "SAF-R001"
R_CONSENT = "SAF-R002"
R_MISSING = "SAF-R003"
R_FAILSAFE = "SAF-R004"
R_TAGS = "SAF-R005"
R_CONTRA = "SAF-R006"
R_UNANALYSABLE = "SAF-R007"
R_PREGNANCY = "SAF-R008"
R_PATHB_NO_RULES = "SAF-R011"
R_OUT_OF_SCOPE = "SAF-R017"
R_RED_FLAG = "SAF-R100"
R_URGENT_STATUS = "SAF-R101"
R_WORSENING = "SAF-R102"
R_RESTRICTION = "SAF-R300"
R_CAUTION_REGION = "SAF-R301"
R_REASSESS = "SAF-R302"
R_CONTENT_UNREVIEWED = "SAF-R013"
R_EXPIRED_RESTRICTION = "SAF-R014"
R_NO_VALID_ITEMS = "SAF-R015"
R_PATH_C = "SAF-R016"
R_BAD_RULE = "SAF-R018"
R_EQUIPMENT = "SAF-R019"
R_LEVEL = "SAF-R020"
_LEVEL_RANK = {"beginner": 0, "intermediate": 1, "advanced": 2}

TERMINAL_STATUSES = {
    s.value for s in (DecisionStatus.STOP_AND_REFER, DecisionStatus.BLOCK_OUT_OF_SCOPE,
                      DecisionStatus.BLOCK_CONSENT, DecisionStatus.NEEDS_INFO, DecisionStatus.ERROR_FAILSAFE)
}


# ----------------------------------------------------------------------------- public API
def evaluate(request: SafetyRequest, rule_set: RuleSet) -> SafetyDecision:
    """Evaluate a request. Never raises: any internal error becomes ERROR_FAILSAFE (SAF-R004)."""
    try:
        return _evaluate(request, rule_set)
    except Exception as exc:  # noqa: BLE001  (fail-safe is the contract)
        return _failsafe(request, rule_set, type(exc).__name__)


def validate_plan(plan_codes: Iterable[str], decision: SafetyDecision, request: SafetyRequest,
                  rule_set: RuleSet) -> Tuple[bool, Tuple[str, ...]]:
    """Second pass (defence in depth, DOC-11 S7 / SAF-R009).

    A plan is valid only if: the decision permits content, the decision matches the request
    (inputs_hash), and a fresh evaluation still allows every exercise in the plan.
    """
    violations: List[str] = []
    if not decision.status.permits_content:
        violations.append(f"decision-status:{decision.status.value}")
    fresh = evaluate(request, rule_set)
    if fresh.inputs_hash != decision.inputs_hash:
        violations.append("stale-decision:inputs-changed")
    if not fresh.status.permits_content:
        violations.append(f"fresh-status:{fresh.status.value}")
    allowed = set(fresh.allowed_codes)
    for code in plan_codes:
        if code not in allowed:
            violations.append(f"not-allowed:{code}")
    return (not violations, tuple(violations))


def find_alternatives(blocked_code: str, relations: Mapping[str, Sequence[Tuple[str, str]]],
                      catalog: Mapping[str, ExerciseCandidate], request: SafetyRequest,
                      rule_set: RuleSet) -> Tuple[str, ...]:
    """DOC-09 §9: alternatives ∪ regressions of `blocked_code`, filtered by the full safety pipeline.

    Returns deterministic order: alternatives first, then regressions, each sorted by code.
    An empty tuple means "no valid alternative" -- callers must say so, never guess.
    """
    rel = relations.get(blocked_code, ())
    wanted = sorted({c for c, r in rel if r == "alternative" and c in catalog and c != blocked_code})
    regress = sorted({c for c, r in rel if r == "regression" and c in catalog and c != blocked_code} - set(wanted))
    ordered = wanted + regress
    if not ordered:
        return ()
    probe = _replace_candidates(request, tuple(catalog[c] for c in ordered))
    decision = evaluate(probe, rule_set)
    allowed = set(decision.allowed_codes)
    return tuple(c for c in ordered if c in allowed)


class SafetyCore:
    """Port implementation (`SafetyGate`) used by workout_engine / ai_gateway."""

    def __init__(self, rule_set: RuleSet):
        self.rule_set = rule_set

    def evaluate(self, request: SafetyRequest) -> SafetyDecision:
        return evaluate(request, self.rule_set)

    def validate_plan(self, plan_codes: Iterable[str], decision: SafetyDecision, request: SafetyRequest):
        return validate_plan(plan_codes, decision, request, self.rule_set)

    def find_alternatives(self, blocked_code, relations, catalog, request):
        return find_alternatives(blocked_code, relations, catalog, request, self.rule_set)


# ----------------------------------------------------------------------------- internals
def _replace_candidates(request: SafetyRequest, candidates: Tuple[ExerciseCandidate, ...]) -> SafetyRequest:
    import dataclasses
    return dataclasses.replace(request, candidates=candidates)


def _make(request: SafetyRequest, rule_set: RuleSet, status: DecisionStatus, *, per_item=(), reasons=(),
          questions=(), urgency=None, pathway=None, flags=()) -> SafetyDecision:
    h = inputs_hash(request, rule_set.version)
    return SafetyDecision(
        decision_id=decision_id_from_hash(h), status=status, per_item=tuple(per_item),
        reasons=tuple(dict.fromkeys(reasons)), required_questions=tuple(questions),
        referral_urgency=urgency, rule_set_version=rule_set.version, inputs_hash=h,
        content_status="published" if rule_set.clinical_content_published else "draft_unreviewed",
        pathway=pathway, flags=tuple(dict.fromkeys(flags)),
    )


def _failsafe(request: SafetyRequest, rule_set: RuleSet, err: str) -> SafetyDecision:
    try:
        h = inputs_hash(request, getattr(rule_set, "version", 0))
    except Exception:  # noqa: BLE001
        import hashlib
        h = hashlib.sha256(f"failsafe:{err}".encode()).hexdigest()
    return SafetyDecision(
        decision_id=decision_id_from_hash(h), status=DecisionStatus.ERROR_FAILSAFE, per_item=(),
        reasons=(R_FAILSAFE, f"internal:{err}"), required_questions=(), referral_urgency=None,
        rule_set_version=getattr(rule_set, "version", 0), inputs_hash=h, content_status="draft_unreviewed",
    )


def _validate(request: SafetyRequest, rule_set: RuleSet) -> None:
    """Structural validation. Programming/data errors raise InvalidInput -> fail-safe."""
    if not isinstance(request, SafetyRequest) or not isinstance(rule_set, RuleSet):
        raise InvalidInput("bad types")
    if rule_set.caution_max_loading not in LOADINGS:
        raise InvalidInput("bad caution_max_loading")
    for c in request.conditions:
        if c.region not in REGIONS or c.problem_type not in PROBLEM_TYPES or c.status not in CONDITION_STATUSES \
                or c.source not in SOURCES:
            raise InvalidInput("bad condition enum")
    for f in request.out_of_scope_flags:
        if f.flag_type not in OUT_OF_SCOPE_TYPES:
            raise InvalidInput("bad out-of-scope flag")
    for r in request.restrictions:
        if r.region is not None and r.region not in REGIONS:
            raise InvalidInput("bad restriction region")
        if r.max_loading is not None and r.max_loading not in LOADINGS:
            raise InvalidInput("bad restriction loading")
        if r.region is None and r.movement_pattern is None and r.exercise_code is None:
            raise InvalidInput("empty restriction")
    for cand in request.candidates:
        for rl in cand.region_loads:
            if rl.region not in REGIONS or rl.loading not in LOADINGS:
                raise InvalidInput("bad region load")
    codes = [c.code for c in request.candidates]
    if len(codes) != len(set(codes)):
        raise InvalidInput("duplicate candidate codes")


def _rule_data(request: SafetyRequest) -> Dict[str, object]:
    return {
        "age": request.age_years,
        "consent": request.consent_health_valid,
        "red_flags": {k: v for k, v in request.red_flag_answers.items()},
        "conditions": [{"region": c.region, "type": c.problem_type, "status": c.status, "source": c.source,
                        "active_pain": c.active_pain, "worsening": c.worsening} for c in request.conditions],
        "out_of_scope": [f.flag_type for f in request.out_of_scope_flags if f.active],
        "context": dict(request.context),
    }


def _clinical_rule_decision(request, rule_set, stage_max: int) -> Optional[SafetyDecision]:
    """Apply data-driven rules up to `stage_max`. Only terminal actions are supported here."""
    data = _rule_data(request)
    for rule in sorted(rule_set.clinical_rules, key=lambda r: (r.stage, r.code)):
        if rule.stage > stage_max:
            continue
        usable = rule.review_status == "published" or rule_set.allow_unreviewed_content
        if not usable:
            continue
        if not jsonlogic.apply(rule.condition, data):
            continue
        status = rule.action.get("status")
        if status not in TERMINAL_STATUSES:
            raise RuleError(f"unsupported rule action in {rule.code}")
        return _make(request, rule_set, DecisionStatus(status), reasons=(rule.code,),
                     urgency=rule.action.get("urgency"))
    return None


def _evaluate(request: SafetyRequest, rule_set: RuleSet) -> SafetyDecision:
    _validate(request, rule_set)

    # ---- stage 1: age / consent / missing data
    if request.user_level is not None and request.user_level not in _LEVEL_RANK:
        raise InvalidInput("bad level")
    if request.age_years is not None and (not isinstance(request.age_years, int) or request.age_years < 0):
        raise InvalidInput("bad age")
    if request.age_years is not None and request.age_years < rule_set.adult_age:
        return _make(request, rule_set, DecisionStatus.BLOCK_OUT_OF_SCOPE, reasons=(R_AGE,))
    if request.consent_health_valid is False:
        return _make(request, rule_set, DecisionStatus.BLOCK_CONSENT, reasons=(R_CONSENT,))
    missing = []
    if request.age_years is None:
        missing.append("age")
    if request.consent_health_valid is None:
        missing.append("consent_health")
    if missing:
        return _make(request, rule_set, DecisionStatus.NEEDS_INFO, reasons=(R_MISSING,), questions=missing)

    # ---- stage 2: out of scope
    active_flags = [f for f in request.out_of_scope_flags if f.active]
    if active_flags:
        code = R_PREGNANCY if any(f.flag_type == "pregnancy" for f in active_flags) else R_OUT_OF_SCOPE
        return _make(request, rule_set, DecisionStatus.BLOCK_OUT_OF_SCOPE, reasons=(code,), urgency="non_urgent")

    # ---- stage 3: red flags (positive answer always stops; conservative even if list is unreviewed)
    positives = sorted(k for k, v in request.red_flag_answers.items() if v is True)
    if positives:
        return _make(request, rule_set, DecisionStatus.STOP_AND_REFER, reasons=(R_RED_FLAG,),
                     urgency=rule_set.reviewed_flag_urgency)
    unanswered = sorted(k for k in rule_set.screening_questions if request.red_flag_answers.get(k) is None)
    if unanswered:
        return _make(request, rule_set, DecisionStatus.NEEDS_INFO, reasons=(R_MISSING,), questions=unanswered)
    term = _clinical_rule_decision(request, rule_set, stage_max=4)
    if term is not None:
        return term

    # ---- stage 4: urgent-referral status recorded
    if any(c.status == "needs_urgent_referral" for c in request.conditions):
        return _make(request, rule_set, DecisionStatus.STOP_AND_REFER, reasons=(R_URGENT_STATUS,), urgency="urgent")

    # ---- clinical-content gate (DOC-09 §8): no content for real users until reviewed lists exist
    if not rule_set.clinical_content_published and not rule_set.allow_unreviewed_content:
        return _make(request, rule_set, DecisionStatus.ERROR_FAILSAFE, reasons=(R_CONTENT_UNREVIEWED,))

    if request.context.get("pathway_c_requested"):
        return _make(request, rule_set, DecisionStatus.STOP_AND_REFER, reasons=(R_PATH_C,), urgency="non_urgent")

    # ---- stage 5: pathway B (new / undiagnosed pain without professional restriction)
    restricted_regions = {r.region for r in request.restrictions if r.region}
    prof_regions = restricted_regions | {c.region for c in request.conditions
                                         if c.source == "professional"
                                         and c.status in ("active_professional_restriction", "professionally_assessed",
                                                          "cleared_to_return")}
    path_b = [c for c in request.conditions
              if c.problem_type == "pain" and c.source == "self_reported" and c.active_pain
              and c.status in ("self_reported_symptom", "no_known_limitation") and c.region not in prof_regions]
    flags: List[str] = []
    reasons: List[str] = []
    pathway: Optional[str] = None
    b_blocked_regions: Set[str] = set()
    if path_b:
        pathway = "B"
        if any(c.worsening for c in path_b):
            return _make(request, rule_set, DecisionStatus.STOP_AND_REFER, reasons=(R_WORSENING,),
                         urgency="non_urgent", pathway="B")
        mapping = dict(rule_set.path_b_related_regions)
        if not rule_set.path_b_activity_rules_published or any(c.region not in mapping for c in path_b):
            return _make(request, rule_set, DecisionStatus.STOP_AND_REFER, reasons=(R_PATHB_NO_RULES,),
                         urgency="non_urgent", pathway="B", flags=("NO_PROGRAM_PATH_B",))
        for c in path_b:
            b_blocked_regions.add(c.region)
            b_blocked_regions.update(mapping[c.region])
        flags.append("PROGRESSION_LOCKED")

    # ---- limited regions from conditions (path A style filters)
    expired = {r for r in request.restrictions if r.valid_until_ordinal is not None
               and r.valid_until_ordinal < request.today_ordinal}
    if expired:
        reasons.append(R_EXPIRED_RESTRICTION)
        flags.append("REASSESSMENT_RECOMMENDED")
    caution_regions: Set[str] = set()      # self-reported only -> limited by caution_max_loading
    hard_regions: Set[str] = set()         # professional condition w/o structured restriction -> fully blocked
    for c in request.conditions:
        if c.status == "no_known_limitation" or c.region in b_blocked_regions:
            continue
        if c.status == "needs_reassessment":
            hard_regions.add(c.region)
            flags.append("REASSESSMENT_RECOMMENDED")
            reasons.append(R_REASSESS)
        elif c.source == "professional" and c.status == "active_professional_restriction" \
                and c.region not in restricted_regions:
            hard_regions.add(c.region)       # SAF-R007: restriction exists but cannot be analysed
            reasons.append(R_UNANALYSABLE)
        elif c.region not in restricted_regions:
            caution_regions.add(c.region)
    if (caution_regions or hard_regions or restricted_regions) and pathway is None:
        pathway = "A"

    limit_names = {c.region for c in request.conditions if c.status != "no_known_limitation"} | restricted_regions
    caution_rank = LOADING_RANK[rule_set.caution_max_loading]

    # ---- stages 6-9: per-item
    results: List[ItemResult] = []
    for cand in sorted(request.candidates, key=lambda x: x.code):
        item_reasons: List[str] = []
        loads = {rl.region: rl.loading for rl in cand.region_loads}
        if cand.review_status != "published" or not cand.safety_tags_complete or set(loads) != set(REGIONS):
            item_reasons.append(R_TAGS)
        if request.equipment is not None and not set(cand.equipment) <= (set(request.equipment) | {"bodyweight"}):
            item_reasons.append(R_EQUIPMENT)
        if request.user_level is not None and _LEVEL_RANK.get(cand.difficulty, 0) > _LEVEL_RANK.get(request.user_level, 0):
            item_reasons.append(R_LEVEL)
        for rs in request.restrictions:
            if rs.exercise_code is not None and rs.exercise_code == cand.code:
                item_reasons.append(R_RESTRICTION)
            if rs.movement_pattern is not None and rs.movement_pattern == cand.movement_pattern:
                item_reasons.append(R_RESTRICTION)
            if rs.region is not None:
                limit = LOADING_RANK[rs.max_loading or "none"]
                load = loads.get(rs.region)
                if load is None or LOADING_RANK[load] > limit:
                    item_reasons.append(R_RESTRICTION)
        for region in hard_regions | b_blocked_regions:
            load = loads.get(region)
            if load is None or load != "none":
                item_reasons.append(R_RESTRICTION)
        for region in caution_regions:
            load = loads.get(region)
            if load is None or LOADING_RANK[load] > caution_rank:
                item_reasons.append(R_CAUTION_REGION)
        for code, region in cand.contraindications:
            if region is None and limit_names:
                item_reasons.append(R_CONTRA)
            elif region is not None and region in limit_names:
                item_reasons.append(R_CONTRA)
        caution = any((region is None and limit_names) or (region in limit_names) for _c, region in cand.cautions)
        results.append(ItemResult(code=cand.code, allowed=not item_reasons,
                                  reasons=tuple(dict.fromkeys(item_reasons)), caution=bool(caution and not item_reasons)))

    any_blocked = any(not r.allowed for r in results)
    any_caution = any(r.caution for r in results)
    modified = any_blocked or any_caution or pathway in ("A", "B")
    if results and not any(r.allowed for r in results):
        return _make(request, rule_set, DecisionStatus.RESTRICT, per_item=results,
                     reasons=tuple(reasons) + (R_NO_VALID_ITEMS,), pathway=pathway, flags=flags)
    status = DecisionStatus.ALLOW_WITH_MODIFICATION if modified else DecisionStatus.ALLOW
    return _make(request, rule_set, status, per_item=results, reasons=reasons, pathway=pathway, flags=flags)

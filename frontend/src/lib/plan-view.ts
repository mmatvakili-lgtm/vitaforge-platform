import type { SafetyDecision, WorkoutPlan } from "./api/generated.ts";

/**
 * The only place that decides whether a plan may be shown. A plan is rendered solely when the Safety Core status permits content
 * AND a plan object exists; every other status shows the decision, never a plan (Safety Core is the sole authority).
 */
export type PlanView =
  | { kind: "plan"; plan: WorkoutPlan; modified: boolean; decision?: SafetyDecision }
  | { kind: "needs_info"; decision: SafetyDecision; questions: string[] }
  | { kind: "needs_consent"; decision: SafetyDecision }
  | { kind: "blocked"; status: SafetyDecision["status"]; decision: SafetyDecision }
  | { kind: "empty" };

// Mirrors safety_core DecisionStatus.permits_content. RESTRICT means "no valid exercise remains" (SAF-R015): it permits NO content.
const PERMITS = new Set<SafetyDecision["status"]>(["ALLOW", "ALLOW_WITH_MODIFICATION"]);

export function permitsPlan(s: SafetyDecision["status"]): boolean {
  return PERMITS.has(s);
}

function asPlan(p: unknown): WorkoutPlan | undefined {
  if (!p || typeof p !== "object") return undefined;
  const o = p as Partial<WorkoutPlan>;
  return typeof o.plan_id === "string" && Array.isArray(o.days) ? (o as WorkoutPlan) : undefined;
}

export function decidePlanView(decision: SafetyDecision | undefined, plan: unknown): PlanView {
  if (!decision) return { kind: "empty" };
  if (decision.status === "NEEDS_INFO") return { kind: "needs_info", decision, questions: decision.required_questions ?? [] };
  if (decision.status === "BLOCK_CONSENT") return { kind: "needs_consent", decision };
  if (!permitsPlan(decision.status)) return { kind: "blocked", status: decision.status, decision };
  const p = asPlan(plan);
  if (!p) return { kind: "blocked", status: "ERROR_FAILSAFE", decision };   // permitting status without a plan is treated as fail-safe, never fabricated
  return { kind: "plan", plan: p, modified: decision.status !== "ALLOW", decision };
}

/** GET /workouts/current returns only a stored plan (the server stores plans only after a permitting decision); no decision object accompanies it. */
export function currentPlanView(plan: unknown): PlanView {
  const p = asPlan(plan);
  return p ? { kind: "plan", plan: p, modified: false } : { kind: "empty" };
}

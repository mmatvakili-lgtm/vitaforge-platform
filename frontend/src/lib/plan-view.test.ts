import { test } from "node:test";
import assert from "node:assert/strict";
import { currentPlanView, decidePlanView, permitsPlan } from "./plan-view.ts";
import type { SafetyDecision } from "./api/generated.ts";

const plan = { plan_id: "p", version_no: 1, safety_decision_id: "d", days: [] };
const d = (status: SafetyDecision["status"], extra: Partial<SafetyDecision> = {}): SafetyDecision => ({ decision_id: "d", status, ...extra });

test("plan is shown only for permitting statuses with a plan object", () => {
  for (const s of ["ALLOW", "ALLOW_WITH_MODIFICATION", "RESTRICT"] as const) assert.equal(decidePlanView(d(s), plan).kind, "plan");
  assert.equal(decidePlanView(d("ALLOW"), plan).kind === "plan" && (decidePlanView(d("ALLOW"), plan) as { modified: boolean }).modified, false);
  assert.equal((decidePlanView(d("RESTRICT"), plan) as { modified: boolean }).modified, true);
});

test("a plan object is NEVER shown for a non-permitting status", () => {
  for (const s of ["NEEDS_INFO", "STOP_AND_REFER", "BLOCK_OUT_OF_SCOPE", "BLOCK_CONSENT", "ERROR_FAILSAFE"] as const) {
    assert.notEqual(decidePlanView(d(s), plan).kind, "plan", s);
    assert.equal(permitsPlan(s), false);
  }
});

test("permitting status without a plan is fail-safe, not fabricated", () => {
  const v = decidePlanView(d("ALLOW"), null);
  assert.equal(v.kind, "blocked");
  assert.equal(decidePlanView(d("ALLOW"), { plan_id: "p" }).kind, "blocked");   // malformed plan
});

test("needs-info carries the questions; consent block is distinct", () => {
  const v = decidePlanView(d("NEEDS_INFO", { required_questions: ["chest_pain"] }), null);
  assert.deepEqual(v.kind === "needs_info" && v.questions, ["chest_pain"]);
  assert.equal(decidePlanView(d("BLOCK_CONSENT"), null).kind, "needs_consent");
  assert.equal(decidePlanView(undefined, null).kind, "empty");
});

test("current plan view requires a well-formed plan", () => {
  assert.equal(currentPlanView(plan).kind, "plan");
  assert.equal(currentPlanView(null).kind, "empty");
  assert.equal(currentPlanView({ nope: 1 }).kind, "empty");
});

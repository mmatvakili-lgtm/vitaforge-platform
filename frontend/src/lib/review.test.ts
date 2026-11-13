import assert from "node:assert/strict";
import { test } from "node:test";
import { blockerKey, canApprove, reviewRequest } from "./review.ts";

test("reject and retire require a written reason; approve does not", () => {
  assert.equal(reviewRequest("reject", "  no "), null);
  assert.deepEqual(reviewRequest("retire", " superseded by new data "), { decision: "retire", notes: "superseded by new data" });
  assert.deepEqual(reviewRequest("approve", ""), { decision: "approve" });
});
test("approval is only offered with zero blockers", () => {
  assert.equal(canApprove([]), true);
  assert.equal(canApprove(["no_source"]), false);
});
test("blocker keys", () => {
  assert.deepEqual(blockerKey("no_source"), { key: "review.blocker.no_source" });
  assert.deepEqual(blockerKey("invalid:basis"), { key: "review.blocker.invalid", detail: "basis" });
});

test("attestations only travel with approve and only when ticked", () => {
  const a = { allergensChecked: true, allergens: ["milk"], licenseChecked: true };
  assert.deepEqual(reviewRequest("approve", "", a), { decision: "approve", allergens: ["milk"], allergens_confirmed: true, license_verified: true });
  assert.deepEqual(reviewRequest("approve", "", { allergensChecked: true, allergens: [], licenseChecked: false }), { decision: "approve", allergens: [], allergens_confirmed: true });
  assert.deepEqual(reviewRequest("approve", "", { allergensChecked: false, allergens: ["milk"], licenseChecked: false }), { decision: "approve" });
  assert.deepEqual(reviewRequest("reject", "wrong data", a), { decision: "reject", notes: "wrong data" });
});

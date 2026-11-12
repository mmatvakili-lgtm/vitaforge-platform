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

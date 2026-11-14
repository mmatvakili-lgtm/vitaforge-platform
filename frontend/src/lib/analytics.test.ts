import assert from "node:assert/strict";
import { test } from "node:test";
import { insightMessageKey, insightParams, sparkRuns } from "./analytics.ts";

test("sparkRuns splits on gaps and handles flat/empty series", () => {
  assert.deepEqual(sparkRuns([null, null], 100, 20), []);
  assert.equal(sparkRuns([5, 5, 5], 100, 20).length, 1);
  const r = sparkRuns([1, 2, null, 3, 4], 100, 20);
  assert.equal(r.length, 2);
  assert.ok(r[0].split(" ").length === 2 && r[1].split(" ").length === 2);
  const [first] = sparkRuns([10, 20], 100, 20)[0].split(" ");
  assert.equal(first, "3.0,17.0");
});

test("insight keys map to messages with a safe fallback", () => {
  assert.equal(insightMessageKey("volume_drop"), "analytics.insight.volume_drop");
  assert.equal(insightMessageKey("<script>"), "analytics.insight.unknown");
  assert.deepEqual(insightParams({ a: 1, b: "x", c: { z: 1 }, d: [1] }), { a: 1, b: "x" });
});

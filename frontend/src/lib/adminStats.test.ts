import assert from "node:assert/strict";
import test from "node:test";
import { barHeights, fmtBytes, groupAuditByDay, pct, sumCounts } from "./adminStats.ts";

test("barHeights scales to the max and never divides by zero", () => {
  assert.deepEqual(barHeights([{ day: 0, count: 2 }, { day: 1, count: 4 }]), [0.5, 1]);
  assert.deepEqual(barHeights([{ day: 0, count: 0 }, { day: 1, count: 0 }]), [0, 0]);
  assert.deepEqual(barHeights([]), []);
});
test("sumCounts / pct / fmtBytes", () => {
  assert.equal(sumCounts([{ day: 0, count: 2 }, { day: 1, count: 3 }]), 5);
  assert.equal(pct(1, 3), 33); assert.equal(pct(1, 0), 0);
  assert.equal(fmtBytes(512), "512 B"); assert.equal(fmtBytes(2048), "2.0 KB"); assert.equal(fmtBytes(3 * 1024 * 1024), "3.0 MB"); assert.equal(fmtBytes(-1), "0 B");
});
test("groupAuditByDay groups consecutive entries of the same UTC day", () => {
  const e = (at: number) => ({ at, actor: "a", action: "x", target: "t", before: null, after: null });
  const g = groupAuditByDay([e(86400 * 5 + 10), e(86400 * 5 + 5), e(86400 * 4)]);
  assert.equal(g.length, 2); assert.equal(g[0].items.length, 2); assert.equal(g[1].day, 86400 * 4);
});

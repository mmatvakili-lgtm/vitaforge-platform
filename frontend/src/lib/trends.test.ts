import assert from "node:assert/strict";
import { test } from "node:test";
import { barPct, weeklyBuckets } from "./trends.ts";

const now = new Date("2026-11-12T10:00:00Z"); // Thursday; Monday of that week = 2026-11-09
test("buckets are Monday-based, oldest first, with empty weeks kept", () => {
  const b = weeklyBuckets([], now, 3);
  assert.deepEqual(b.map((x) => x.weekStart), ["2026-10-26", "2026-11-02", "2026-11-09"]);
  assert.ok(b.every((x) => x.sessions === 0));
});
test("sums finished sessions, ignores in-progress, invalid and out-of-range ones", () => {
  const b = weeklyBuckets([
    { id: "1", status: "completed", started_at: "2026-11-10T08:00:00Z", volume_kg: 100, sets_done: 5 },
    { id: "2", status: "aborted", started_at: "2026-11-09T00:00:00Z", volume_kg: 50, sets_done: 2 },
    { id: "3", status: "in_progress", started_at: "2026-11-11T08:00:00Z", volume_kg: 999, sets_done: 9 },
    { id: "4", status: "completed", started_at: "garbage", volume_kg: 5 },
    { id: "5", status: "completed", started_at: "2020-01-01T00:00:00Z", volume_kg: 5 },
    { id: "6", status: "completed", started_at: "2026-11-02T12:00:00Z" },
  ], now, 2);
  assert.deepEqual(b[1], { weekStart: "2026-11-09", sessions: 2, volumeKg: 150, sets: 7 });
  assert.deepEqual(b[0], { weekStart: "2026-11-02", sessions: 1, volumeKg: 0, sets: 0 });
});
test("Sunday belongs to the previous Monday's week", () => {
  const b = weeklyBuckets([{ id: "s", status: "completed", started_at: "2026-11-15T20:00:00Z", volume_kg: 10 }], new Date("2026-11-15T21:00:00Z"), 1);
  assert.equal(b[0].weekStart, "2026-11-09"); assert.equal(b[0].volumeKg, 10);
});
test("barPct", () => {
  assert.equal(barPct(0, 10), 0); assert.equal(barPct(1, 1000), 4); assert.equal(barPct(10, 10), 100); assert.equal(barPct(5, 0), 0);
});

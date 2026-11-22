import assert from "node:assert/strict";
import { test } from "node:test";
import { journey, pickTodayDay, PRIMARY_NAV, MORE_NAV, MORE_GROUPS } from "./journey.ts";

const base = { onboardingDone: true, assessed: true, hasPlan: true, totalSessions: 5, sessionsThisWeek: 3, plannedPerWeek: 3 };

test("a new user is sent to onboarding first, then assessment, then plan", () => {
  assert.equal(journey({ ...base, onboardingDone: false, assessed: false, hasPlan: false, totalSessions: 0, sessionsThisWeek: 0 }).next, "onboarding");
  assert.equal(journey({ ...base, assessed: false, hasPlan: false, totalSessions: 0, sessionsThisWeek: 0 }).next, "assessment");
  assert.equal(journey({ ...base, hasPlan: false, totalSessions: 0, sessionsThisWeek: 0 }).next, "plan");
});
test("with a plan, training is next until the weekly target is met, then review", () => {
  assert.equal(journey({ ...base, sessionsThisWeek: 1 }).next, "train");
  assert.equal(journey(base).next, "review");
  assert.equal(journey({ ...base, plannedPerWeek: 0, sessionsThisWeek: 0 }).next, "train");
  assert.equal(journey({ ...base, plannedPerWeek: 0, sessionsThisWeek: 2 }).next, "review");
});
test("done flags count progress", () => {
  const j = journey({ ...base, totalSessions: 1 });
  assert.deepEqual(j.steps.map((s) => s.done), [true, true, true, true, false]);
  assert.equal(j.doneCount, 4);
});
test("today's day follows the last trained day and wraps", () => {
  const days = [{ title: "A" }, { title: "B" }, { title: "C" }];
  assert.equal(pickTodayDay(days, null)?.title, "A");
  assert.equal(pickTodayDay(days, "A")?.title, "B");
  assert.equal(pickTodayDay(days, "C")?.title, "A");
  assert.equal(pickTodayDay(days, "zzz")?.title, "A");
  assert.equal(pickTodayDay([], "A"), undefined);
});
test("navigation groups do not overlap and keep the primary bar short", () => {
  assert.ok(PRIMARY_NAV.length <= 4);
  for (const k of PRIMARY_NAV) assert.ok(!(MORE_NAV as readonly string[]).includes(k));
});

test("More groups partition MORE_NAV exactly (no item lost or duplicated)", () => {
  const flat = MORE_GROUPS.flatMap((g) => [...g.items]);
  assert.deepEqual([...flat].sort(), [...MORE_NAV].sort());
});

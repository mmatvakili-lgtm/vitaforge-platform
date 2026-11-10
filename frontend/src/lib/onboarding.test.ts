import { test } from "node:test";
import assert from "node:assert/strict";
import { allScreeningAnswered, parseIntField, resumeStage, SCREENING_QUESTIONS, validateBasics, validateEquipment, validateGoal, validateSchedule } from "./onboarding.ts";

test("validators match server rules", () => {
  assert.deepEqual(validateBasics({ age: 30 }), {});
  assert.ok(validateBasics({ age: 0 }).age && validateBasics({ age: 120 }).age && validateBasics({ age: 3.5 }).age && validateBasics({}).age);
  assert.deepEqual(validateGoal({ goal: "strength", level: "beginner" }), {});
  assert.deepEqual(Object.keys(validateGoal({ goal: "x", level: "y" })).sort(), ["goal", "level"]);
  assert.deepEqual(validateSchedule({ days_per_week: 6, session_minutes: 20 }), {});
  assert.ok(validateSchedule({ days_per_week: 7, session_minutes: 60 }).days_per_week);
  assert.ok(validateSchedule({ days_per_week: 3, session_minutes: 19 }).session_minutes);
  assert.ok(validateSchedule({ days_per_week: 3, session_minutes: 181 }).session_minutes);
  assert.deepEqual(validateEquipment({ equipment: [] }), {});
  assert.ok(validateEquipment({ equipment: ["jetpack"] }).equipment);
});

test("parseIntField accepts digits only", () => {
  assert.equal(parseIntField(" 42 "), 42);
  assert.equal(parseIntField("4.2"), undefined);
  assert.equal(parseIntField("-1"), undefined);
  assert.equal(parseIntField(""), undefined);
});

test("resume goes to the first missing server step, then consent, screening, finish", () => {
  assert.equal(resumeStage(undefined, false), "basics");
  assert.equal(resumeStage({ current_step: 3, summary_ready: false }, false), "schedule");
  assert.equal(resumeStage({ current_step: 4, summary_ready: true }, false), "consent");
  assert.equal(resumeStage({ current_step: 4, summary_ready: true, safety_screening_complete: false }, true), "screening");
  assert.equal(resumeStage({ current_step: 4, summary_ready: true, safety_screening_complete: true }, true), "finish");
});

test("screening needs every question answered", () => {
  assert.equal(allScreeningAnswered({ chest_pain: false }), false);
  assert.equal(allScreeningAnswered(Object.fromEntries(SCREENING_QUESTIONS.map((q) => [q, false]))), true);
});

test("priority muscles and environment are optional but validated", () => {
  assert.deepEqual(validateGoal({ goal: "strength", level: "beginner", priority_muscles: ["chest", "lats"] }), {});
  assert.ok(validateGoal({ goal: "strength", level: "beginner", priority_muscles: ["chest", "lats", "glutes", "calves"] }).priority_muscles);
  assert.ok(validateGoal({ goal: "strength", level: "beginner", priority_muscles: ["x"] }).priority_muscles);
  assert.deepEqual(validateEquipment({ equipment: [], environment: "home" }), {});
  assert.ok(validateEquipment({ equipment: [], environment: "moon" }).environment);
});

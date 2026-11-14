import assert from "node:assert/strict";
import { test } from "node:test";
import { buildAnswers, STEPS } from "./assessment.ts";

test("blank fields are skipped, digits normalised, booleans mapped", () => {
  const r = buildAnswers({ squat_reps: "۲۵", squat_heels_down: "no", push_variant: "knee", plank_s: "" });
  assert.ok(r.ok);
  if (r.ok) assert.deepEqual(r.answers, { squat_reps: 25, squat_heels_down: false, push_variant: "knee" });
});
test("empty form, out-of-range, decimals and unknown enum are rejected per field", () => {
  assert.deepEqual(buildAnswers({}), { ok: false, errors: { _form: "empty" } });
  const r = buildAnswers({ squat_reps: "101", plank_s: "5.5", push_variant: "x", squat_heels_down: "maybe" });
  assert.ok(!r.ok);
  if (!r.ok) assert.deepEqual(Object.keys(r.errors).sort(), ["plank_s", "push_variant", "squat_heels_down", "squat_reps"]);
});
test("pain regions are de-duplicated and sent only when present", () => {
  const r = buildAnswers({ plank_s: "30" }, ["knee", "knee"]);
  assert.ok(r.ok);
  if (r.ok) assert.deepEqual(r.answers.pain_regions, ["knee"]);
  const q = buildAnswers({ plank_s: "30" });
  assert.ok(q.ok && q.ok && !("pain_regions" in q.answers));
});
test("every field key is unique and ranges mirror the server bounds", () => {
  const keys = STEPS.flatMap((s) => s.fields.map((f) => f.key));
  assert.equal(new Set(keys).size, keys.length);
  const f = STEPS[0].fields[0];
  assert.ok(f.kind === "int" && f.max === 100);
});

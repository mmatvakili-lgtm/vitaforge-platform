import { test } from "node:test";
import assert from "node:assert/strict";
import { buildSetLog, finishRequest, isLogged, newUuid, nextSet, plannedSets, progress, skipSetLog, type PlannedSet } from "./workout-log.ts";
import { libraryQuery, NO_FILTERS, pageCount } from "./exercises.ts";

const P: PlannedSet = { exerciseId: "e1", name: "Squat", setNo: 1, repsMin: 8, repsMax: 10 };

test("set log validation mirrors the server", () => {
  const ok = buildSetLog(P, { reps: "۸", load: "۲۰٫۵", rpe: "7" }, "u1");
  assert.ok(ok.ok && ok.body.reps === 8 && ok.body.load_kg === 20.5 && ok.body.rpe === 7 && ok.body.client_uuid === "u1");
  assert.deepEqual(buildSetLog(P, { reps: "8", load: "", rpe: "" }, "u").ok && (buildSetLog(P, { reps: "8", load: "", rpe: "" }, "u") as { ok: true; body: { load_kg: number } }).body.load_kg, 0);
  for (const bad of [{ reps: "0", load: "", rpe: "" }, { reps: "201", load: "", rpe: "" }, { reps: "x", load: "", rpe: "" }, { reps: "8", load: "-1", rpe: "" },
    { reps: "8", load: "1001", rpe: "" }, { reps: "8", load: "", rpe: "11" }, { reps: "8.5", load: "", rpe: "" }]) assert.equal(buildSetLog(P, bad, "u").ok, false);
  const plank: PlannedSet = { exerciseId: "e2", name: "Plank", setNo: 1, durationSec: 30 };
  const t = buildSetLog(plank, { reps: "", load: "", rpe: "" }, "u");
  assert.ok(t.ok && t.body.duration_sec === 30 && t.body.reps === undefined);
});

test("skip, planning, progress and next set", () => {
  assert.deepEqual(skipSetLog(P, "u"), { client_uuid: "u", exercise_id: "e1", set_no: 1, skipped: true, skipped_reason: "skipped_by_user" });
  const sets = plannedSets({ exercises: [{ exercise_id: "w", name: "Warm", role: "warmup", sets: [{ set_no: 1 }] }, { exercise_id: "e1", name: "Squat", role: "main", sets: [{ set_no: 1, reps_min: 8, reps_max: 10 }, { set_no: 2, reps_min: 8, reps_max: 10 }] }] });
  assert.equal(sets.length, 2);
  const s = { logged_sets: [{ exercise_id: "e1", set_no: 1 }] };
  assert.equal(isLogged(s, sets[0]), true);
  assert.deepEqual(progress(s as never, sets), { done: 1, total: 2 });
  assert.equal(nextSet(s as never, sets)?.setNo, 2);
});

test("finish request and ids", () => {
  assert.deepEqual(finishRequest({ difficulty: "7", stoppedForPain: true, notes: " ok " }), { perceived_difficulty: 7, aborted_reason: "pain", notes: "ok" });
  assert.deepEqual(finishRequest({ difficulty: "11" }), {});
  assert.match(newUuid(), /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test("library query only carries active filters", () => {
  assert.deepEqual(libraryQuery(NO_FILTERS, 1), { page: 1, page_size: 20 });
  assert.deepEqual(libraryQuery({ q: " squat ", muscle: "quadriceps", equipment: "", difficulty: "beginner" }, 3), { page: 3, page_size: 20, q: "squat", muscle: "quadriceps", difficulty: "beginner" });
  assert.equal(pageCount(0), 1); assert.equal(pageCount(41), 3);
});

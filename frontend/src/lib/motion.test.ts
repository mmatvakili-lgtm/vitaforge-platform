import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { L, TEMPLATES, bounds, ik, motionFor, poseAt, solve } from "./motion.ts";

const codes: [string, string][] = JSON.parse(readFileSync(new URL("./motion.codes.json", import.meta.url), "utf8"));
const d = (a: readonly [number, number], b: readonly [number, number]) => Math.hypot(a[0] - b[0], a[1] - b[1]);

test("ik keeps bone lengths and reaches reachable targets", () => {
  const r = ik([0, 100], [30, 40], 56, 54, 1);
  assert.ok(Math.abs(d([0, 100], r.mid) - 56) < 1e-6 && Math.abs(d(r.mid, r.end) - 54) < 1e-6);
  assert.ok(d(r.end, [30, 40]) < 1e-6);
  const far = ik([0, 0], [500, 0], 56, 54, 1);                       // out of reach -> straight, never NaN
  assert.ok(Number.isFinite(far.mid[0]) && Math.abs(far.end[0] - 109.999) < 0.01);
});

test("every template solves to finite joints with constant bone lengths along the whole loop", () => {
  for (const [key, tpl] of Object.entries(TEMPLATES)) {
    assert.ok(tpl.frames.length >= 2 && tpl.targets.length > 0, key);
    for (let i = 0; i < 40; i++) {
      const s = solve(poseAt(tpl, i / 40));
      for (const p of Object.values(s)) assert.ok(Number.isFinite(p[0]) && Number.isFinite(p[1]), `${key} NaN`);
      assert.ok(Math.abs(d(s.hip, s.kneeA) - L.thigh) < 1e-6 && Math.abs(d(s.shoulder, s.elbowA) - L.upper) < 1e-6, `${key} bone length`);
    }
  }
});

test("standing feet never sink below the floor and the figure stays in a sane box", () => {
  for (const [key, tpl] of Object.entries(TEMPLATES)) {
    const b = bounds(tpl.frames);
    assert.ok(b.maxX - b.minX < 420 && b.maxY - b.minY < 360, `${key} too large`);
    if (!/hang|pull|dip/.test(key)) assert.ok(b.minY > -14, `${key} below floor (${b.minY.toFixed(1)})`);
  }
});

test("all 229 starter exercises get a specific template (no generic fallback)", () => {
  const generic = codes.filter(([c, p]) => !motionFor(c, p).exact).map(([c]) => c);
  assert.deepEqual(generic, []);
});

test("implements follow the exercise name", () => {
  assert.ok(motionFor("kettlebell_goblet_squat").template.props.includes("kettlebell"));
  assert.ok(!motionFor("bodyweight_squat").template.props.includes("dumbbell"));
  assert.ok(motionFor("barbell_back_squat").template.props.includes("barbell-back"));
  assert.ok(motionFor("push_up").template.key === "pushup" && motionFor("knee_push_up").template.key === "pushup_knee");
});

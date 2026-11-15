import assert from "node:assert/strict";
import { test } from "node:test";
import { BODY_REGIONS, buildMesh, hexToRgb, pickRegion, renderMesh, shade } from "./body3d.ts";

const mesh = buildMesh();
const O = { yaw: 0, pitch: 0, width: 300, height: 500 };

test("mesh is deterministic and covers every muscle region", () => {
  assert.equal(mesh.idx.length % 3, 0);
  assert.equal(mesh.triRegion.length, mesh.idx.length / 3);
  for (const r of ["chest", "quadriceps", "hamstrings", "glutes", "lats", "calves", "abdominals"]) assert.ok(BODY_REGIONS.includes(r) && mesh.regions.includes(r), r);
  assert.deepEqual(renderMesh(mesh, O).length, renderMesh(buildMesh(), O).length);
});

test("front view puts the chest nearest the camera, back view the lats", () => {
  const nearest = (yaw: number, region: string) => Math.max(...renderMesh(mesh, { ...O, yaw }).filter((t) => t.region === region).map((t) => t.depth));
  assert.ok(nearest(0, "chest") > nearest(0, "lats"));
  assert.ok(nearest(Math.PI, "lats") > nearest(Math.PI, "chest"));
});

test("a full turn returns to the same picture", () => {
  const a = renderMesh(mesh, O), b = renderMesh(mesh, { ...O, yaw: Math.PI * 2 });
  assert.equal(a.length, b.length);
  assert.ok(Math.abs(a[10].x[0] - b[10].x[0]) < 0.01);
});

test("triangles are drawn far to near and stay on the canvas", () => {
  const t = renderMesh(mesh, O);
  for (let i = 1; i < t.length; i++) assert.ok(t[i - 1].depth <= t[i].depth);
  const xs = t.flatMap((q) => q.x), ys = t.flatMap((q) => q.y);
  assert.ok(Math.min(...xs) >= 0 && Math.max(...xs) <= O.width && Math.min(...ys) >= 0 && Math.max(...ys) <= O.height);
});

test("picking returns the region of the nearest triangle and null on background", () => {
  const t = renderMesh(mesh, O);
  const q = [...t].reverse().find((x) => x.region === "quadriceps")!;
  const cx = (q.x[0] + q.x[1] + q.x[2]) / 3, cy = (q.y[0] + q.y[1] + q.y[2]) / 3;
  assert.equal(pickRegion(t, cx, cy), "quadriceps");
  assert.equal(pickRegion(t, 1, 1), null);
});

test("colour helpers", () => {
  assert.deepEqual(hexToRgb("#ff5a1f"), [255, 90, 31]);
  assert.deepEqual(hexToRgb("fff"), [255, 255, 255]);
  assert.equal(shade([100, 100, 100], 0), "rgb(38,38,38)");
  assert.equal(shade([255, 255, 255], 1), "rgb(255,255,255)");
});

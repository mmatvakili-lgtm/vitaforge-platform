import assert from "node:assert/strict";
import { test } from "node:test";
import { BODY_METRICS, parseMeasurement } from "./body.ts";

test("parses Latin, Persian and Arabic-Indic digits and decimal separators", () => {
  assert.equal(parseMeasurement("weight", "72.5"), 72.5);
  assert.equal(parseMeasurement("weight", "۷۲٫۵"), 72.5);
  assert.equal(parseMeasurement("weight", "٧٢,٥"), 72.5);
});
test("rejects empty, non-numeric, negative, NaN-like and out-of-range values", () => {
  for (const bad of ["", " ", "abc", "-5", "1e3", "Infinity", "NaN", "7 2", "19.9", "400.1"]) assert.equal(parseMeasurement("weight", bad), null, bad);
  assert.equal(parseMeasurement("body_fat_pct", "0.5"), null);
});
test("bounds are inclusive and match the server table", () => {
  assert.equal(parseMeasurement("height", "80"), 80);
  assert.equal(parseMeasurement("height", "250"), 250);
  assert.equal(BODY_METRICS.body_fat_pct.unit, "%");
});

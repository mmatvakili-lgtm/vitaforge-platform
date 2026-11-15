import assert from "node:assert/strict";
import { test } from "node:test";
import { clock, restFraction, restRemaining } from "./rest-timer.ts";

test("remaining seconds are wall-clock based and never negative", () => {
  assert.equal(restRemaining(10_000, 0), 10);
  assert.equal(restRemaining(10_000, 9_100), 1);
  assert.equal(restRemaining(10_000, 12_000), 0);
});

test("clock and fraction", () => {
  assert.equal(clock(75), "1:15");
  assert.equal(clock(5), "0:05");
  assert.equal(clock(-3), "0:00");
  assert.equal(restFraction(60, 30), 0.5);
  assert.equal(restFraction(0, 0), 1);
  assert.equal(restFraction(60, 90), 0);
});

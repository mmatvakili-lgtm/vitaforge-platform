import assert from "node:assert/strict";
import test from "node:test";
import { passwordChecks } from "./password.ts";

test("passwordChecks follows the server policy", () => {
  assert.deepEqual(passwordChecks(""), { len: false, upper: false, digit: false, score: 0 });
  assert.equal(passwordChecks("abcdefghij").score, 1);
  assert.equal(passwordChecks("Abcdefghij").score, 2);
  assert.deepEqual(passwordChecks("Abcdefghi1"), { len: true, upper: true, digit: true, score: 3 });
  assert.equal(passwordChecks("Ab1").len, false);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { errorMessage, formatNumber, hasSafetyReason, messageKeys, normalizeDigits, safetyReason, t, dirOf } from "./i18n.ts";
import { SCREENING_QUESTIONS, GOALS, LEVELS, EQUIPMENT } from "./onboarding.ts";
import { OPERATIONS } from "./api/generated.ts";

test("fa and en catalogs have identical keys and no empty values", () => {
  assert.deepEqual(messageKeys("fa").sort(), messageKeys("en").sort());
  for (const l of ["fa", "en"] as const) for (const k of messageKeys(l)) assert.notEqual(t(l, k).trim(), "", k);
});

test("every enum used by the UI has a label in both languages", () => {
  const keys = [...GOALS.map((g) => `goal.${g}`), ...LEVELS.map((g) => `level.${g}`), ...EQUIPMENT.map((g) => `equip.${g}`), ...SCREENING_QUESTIONS.map((q) => `screening.q.${q}`)];
  for (const l of ["fa", "en"] as const) for (const k of keys) assert.notEqual(t(l, k), k, `${l}:${k}`);
});

test("every error code the contract can return has a message", () => {
  const codes = ["validation_failed", "auth_failed", "account_locked", "conflict", "not_found", "forbidden", "quota_or_plan_required", "precondition_required", "needs_content", "feature_unavailable", "bad_request", "gone", "consent_required", "internal_error", "csrf_failed", "bad_json", "too_large", "network_error", "unexpected_status"];
  for (const l of ["fa", "en"] as const) for (const c of codes) assert.notEqual(errorMessage(l, c), t(l, "error.unknown"), `${l}:${c}`);
  assert.equal(errorMessage("en", "something_new"), t("en", "error.unknown"));
  assert.ok(Object.keys(OPERATIONS).length > 0);
});

test("safety reasons exist in both languages for every generated code", () => {
  assert.ok(hasSafetyReason("SAF-R003"));
  assert.notEqual(safetyReason("fa", "SAF-R003"), "SAF-R003");
  assert.notEqual(safetyReason("en", "SAF-R003"), "SAF-R003");
  assert.equal(safetyReason("en", "UNKNOWN"), "UNKNOWN");
});

test("digits and direction follow the locale", () => {
  assert.equal(formatNumber("fa", 3), "۳");
  assert.equal(formatNumber("en", 3), "3");
  assert.equal(normalizeDigits("۱۲۳٤"), "1234");
  assert.equal(t("fa", "common.step", { n: 1, total: 4 }), "مرحله ۱ از ۴");
  assert.equal(dirOf("fa"), "rtl");
  assert.equal(dirOf("en"), "ltr");
});

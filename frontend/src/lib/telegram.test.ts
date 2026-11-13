import assert from "node:assert/strict";
import { test } from "node:test";
import { clock, linkErrorKey, pollOutcome, safeDeepLink, secondsLeft } from "./telegram.ts";

test("link errors map to states without revealing whether the account exists", () => {
  assert.equal(linkErrorKey(401).key, "telegram.linkFailed");
  assert.equal(linkErrorKey(404).key, "telegram.linkFailed");
  assert.equal(linkErrorKey(503).phase, "unavailable");
  assert.equal(linkErrorKey(429).key, "telegram.rateLimited");
  assert.equal(linkErrorKey(409).phase, "verified");
});
test("only genuine t.me deep links are accepted", () => {
  const ok = "https://t.me/vitaforge_bot?start=" + "a".repeat(32);
  assert.equal(safeDeepLink(ok), ok);
  for (const bad of ["http://t.me/vitaforge_bot?start=" + "a".repeat(32), "https://evil.example/?start=" + "a".repeat(32), "javascript:alert(1)", "https://t.me/vitaforge_bot?start=short", "https://t.me/vitaforge_bot?start=" + "a".repeat(32) + "&x=1"]) assert.equal(safeDeepLink(bad), null);
});
test("countdown", () => {
  const now = Date.parse("2026-01-01T00:00:00Z");
  assert.equal(secondsLeft("2026-01-01T00:10:00Z", now), 600);
  assert.equal(secondsLeft("2025-12-31T23:00:00Z", now), 0);
  assert.equal(secondsLeft("garbage", now), 0);
  assert.equal(clock(65), "1:05");
});
test("poll outcomes: success only on 200, 401 keeps waiting", () => {
  assert.equal(pollOutcome(200), "verified");
  assert.equal(pollOutcome(401), "wait");
  assert.equal(pollOutcome(423), "locked");
  assert.equal(pollOutcome(500), "error");
});

import { readFileSync } from "node:fs";
test("regression: TelegramVerify re-arms its mounted flag (React StrictMode mount/cleanup/mount left the button stuck on 'sending')", () => {
  const src = readFileSync(new URL("../components/TelegramVerify.tsx", import.meta.url), "utf8");
  assert.match(src, /alive\.current = true/);
});

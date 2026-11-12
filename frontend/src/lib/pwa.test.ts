import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const sw = readFileSync(new URL("../../public/sw.js", import.meta.url), "utf8");
test("service worker never caches API traffic or non-GET requests", () => {
  assert.match(sw, /startsWith\("\/api\/"\)\) return/);
  assert.match(sw, /req\.method !== "GET"/);
  assert.doesNotMatch(sw, /cache\.addAll|c\.put\(req, res\.clone\(\)\);[^}]*api/);
});
test("manifest is valid JSON with required fields", () => {
  const m = JSON.parse(readFileSync(new URL("../../public/manifest.webmanifest", import.meta.url), "utf8"));
  for (const k of ["name", "start_url", "display", "icons"]) assert.ok(m[k], k);
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { buildUrl, createClient, invalidFields } from "./client.ts";
import { OPERATIONS } from "./generated.ts";

function fake(status: number, body: unknown, seen: { url?: string; init?: RequestInit }[] = []): typeof fetch {
  return (async (url: string, init: RequestInit) => {
    seen.push({ url, init });
    return new Response(body === undefined ? "" : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
}

test("contract has all 86 operations", () => {
  assert.equal(Object.keys(OPERATIONS).length, 86);
});

test("buildUrl fills path params, encodes and skips empty query", () => {
  assert.equal(buildUrl("/api/v1/", "/exercises/{exercise_id}", { exercise_id: "a b" }, { q: undefined, page: 2 }), "/api/v1/exercises/a%20b?page=2");
  assert.throws(() => buildUrl("/api/v1", "/exercises/{exercise_id}", {}));
});

test("POST sends JSON, CSRF header from cookie and same-origin credentials", async () => {
  const seen: { url?: string; init?: RequestInit }[] = [];
  const c = createClient({ fetchImpl: fake(200, { user_id: "u" }, seen), readCookie: (n) => (n === "csrftoken" ? "tok" : undefined) });
  const r = await c.call("API-AUTH-003", { body: { identifier: "a@b.c", password: "x" } });
  assert.equal(r.ok, true);
  assert.equal(seen[0].url, "/api/v1/auth/login");
  const h = seen[0].init!.headers as Record<string, string>;
  assert.equal(h["X-CSRFToken"], "tok");
  assert.equal(seen[0].init!.credentials, "same-origin");
  assert.equal(h["Authorization"], undefined);            // web contract: cookie session only, never a Bearer token
});

test("GET sends no CSRF header and no body", async () => {
  const seen: { url?: string; init?: RequestInit }[] = [];
  const c = createClient({ fetchImpl: fake(200, {}, seen), readCookie: () => "tok" });
  await c.call("API-ONB-001");
  assert.equal(seen[0].init!.method, "GET");
  assert.equal(seen[0].init!.body, undefined);
  assert.equal((seen[0].init!.headers as Record<string, string>)["X-CSRFToken"], undefined);
});

test("error envelope is mapped", async () => {
  const c = createClient({ fetchImpl: fake(422, { code: "validation_failed", message: "m", request_id: "r1", details: { fields: [{ path: "age" }] } }), readCookie: () => undefined });
  const r = await c.call("API-ONB-002", { path: { step: "1" }, body: { answers: { age: 0 } } });
  assert.equal(r.ok, false);
  if (!r.ok) {
    assert.equal(r.error.code, "validation_failed");
    assert.equal(r.error.requestId, "r1");
    assert.deepEqual(invalidFields(r.error), ["age"]);
  }
});

test("network failure and non-JSON error bodies do not throw", async () => {
  const boom = (async () => { throw new TypeError("x"); }) as unknown as typeof fetch;
  const r1 = await createClient({ fetchImpl: boom, readCookie: () => undefined }).call("API-ONB-001");
  assert.ok(!r1.ok && r1.error.code === "network_error" && r1.status === 0);
  const html = (async () => new Response("<html>", { status: 502 })) as unknown as typeof fetch;
  const r2 = await createClient({ fetchImpl: html, readCookie: () => undefined }).call("API-ONB-001");
  assert.ok(!r2.ok && r2.error.code === "unexpected_status");
});

test("cacheMs: identical GETs share one request, writes clear the cache, errors are not cached", async () => {
  let n = 0;
  const fetchImpl = (async (_u: string, init?: RequestInit) => { n++; return new Response(init?.method === "GET" ? "{}" : "{}", { status: n === 4 ? 500 : 200 }); }) as unknown as typeof fetch;
  const c = createClient({ fetchImpl, cacheMs: 5000, readCookie: () => undefined });
  await Promise.all([c.call("API-PRO-001"), c.call("API-PRO-001")]);
  assert.equal(n, 1);
  await c.call("API-AUTH-004");                       // a write clears the cache
  await c.call("API-PRO-001");
  assert.equal(n, 3);
  const bad = await c.call("API-DASH-001");           // 500 is returned but not cached
  assert.equal(bad.ok, false);
  await c.call("API-DASH-001");
  assert.equal(n, 5);
});

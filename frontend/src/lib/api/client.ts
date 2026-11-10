// Typed client for the VitaForge OpenAPI contract (see generated.ts). Framework-free: the same code runs in the browser, in Next and in tests.
import { OPERATIONS, type OpId, type OpTypes } from "./generated.ts";

export type ApiError = { status: number; code: string; message: string; requestId?: string; details?: unknown };
export type Result<T> = { ok: true; status: number; data: T } | { ok: false; status: number; error: ApiError };

export interface ClientOptions {
  baseUrl?: string;                                     // default "/api/v1" (same origin; Next proxies to Django)
  fetchImpl?: typeof fetch;
  readCookie?: (name: string) => string | undefined;   // default: document.cookie (browser)
}

type CallArgs<K extends OpId> = { path?: OpTypes[K]["path"]; query?: OpTypes[K]["query"]; body?: OpTypes[K]["body"] };

export function browserCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const hit = document.cookie.split("; ").find((c) => c.startsWith(name + "="));
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : undefined;
}

export function buildUrl(base: string, template: string, path: Record<string, string> = {}, query: Record<string, unknown> = {}): string {
  const p = template.replace(/\{(\w+)\}/g, (_, k: string) => {
    if (path[k] === undefined) throw new Error(`missing path parameter ${k}`);
    return encodeURIComponent(path[k]);
  });
  const qs = Object.entries(query).filter(([, v]) => v !== undefined && v !== null).map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
  return base.replace(/\/$/, "") + p + (qs ? "?" + qs : "");
}

export function createClient(opts: ClientOptions = {}) {
  const base = opts.baseUrl ?? "/api/v1";
  const doFetch = opts.fetchImpl ?? ((...a: Parameters<typeof fetch>) => fetch(...a));
  const cookie = opts.readCookie ?? browserCookie;

  async function call<K extends OpId>(id: K, args: CallArgs<K> = {}): Promise<Result<OpTypes[K]["res"]>> {
    const op = OPERATIONS[id];
    const headers: Record<string, string> = { Accept: "application/json" };
    let body: string | undefined;
    if (op.method !== "GET") {
      headers["Content-Type"] = "application/json";
      const csrf = cookie("csrftoken");
      if (csrf) headers["X-CSRFToken"] = csrf;           // double-submit CSRF (ADR-0009)
      body = JSON.stringify(args.body ?? {});
    }
    let res: Response;
    try {
      res = await doFetch(buildUrl(base, op.path, args.path as Record<string, string>, args.query as Record<string, unknown>), {
        method: op.method, headers, body, credentials: "same-origin", cache: "no-store",
      });
    } catch {
      return { ok: false, status: 0, error: { status: 0, code: "network_error", message: "network error" } };
    }
    const text = await res.text();
    let json: unknown = undefined;
    if (text) {
      try { json = JSON.parse(text); } catch { json = undefined; }
    }
    if (res.ok) return { ok: true, status: res.status, data: json as OpTypes[K]["res"] };
    const b = (json ?? {}) as { code?: string; message?: string; request_id?: string; details?: unknown };
    return { ok: false, status: res.status, error: { status: res.status, code: b.code ?? "unexpected_status", message: b.message ?? "", requestId: b.request_id, details: b.details } };
  }

  return { call };
}

export type ApiClient = ReturnType<typeof createClient>;

/** Field paths the server reported as invalid (`details.fields[].path`); values are never echoed by the server. */
export function invalidFields(e: ApiError): string[] {
  const f = (e.details as { fields?: Array<{ path?: string }> } | undefined)?.fields;
  return Array.isArray(f) ? f.map((x) => x.path ?? "").filter(Boolean) : [];
}

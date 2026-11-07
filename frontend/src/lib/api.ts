const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export type ApiResult<T> = { ok: true; data: T } | { ok: false; status: number; error: string; reasons?: string[] };

export async function api<T>(method: string, path: string, token?: string, body?: unknown): Promise<ApiResult<T>> {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: method === "GET" ? undefined : JSON.stringify(body ?? {}),
  });
  const json = await res.json().catch(() => ({}));
  return res.ok ? { ok: true, data: json as T } : { ok: false, status: res.status, error: json.error ?? "error", reasons: json.reasons };
}

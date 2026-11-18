/** Admin panel: pure media-resolution logic + a tiny typed client for the (non-OpenAPI) /admin routes. */
export type View = "photo" | "video" | "3d";
export interface MediaOverride {
  photo?: boolean; video?: boolean; anim3d?: boolean; default?: View; video_id?: string; video_title?: string; photo_file?: string; note?: string; reviewed?: boolean;
}
export interface BaseMedia { hasPhoto: boolean; video: { id: string; title: string } | null }
export interface Resolved {
  views: View[]; initial: View | null;
  photoFile: string | null;                                        // uploaded replacement (single image) or null → the bundled two-frame reference photos
  video: { id: string; title: string } | null;
}

/** What to show for one exercise: bundled media, adjusted by the admin override (disabled kinds are removed; replacements win). */
export function resolveMedia(base: BaseMedia, o: MediaOverride | undefined): Resolved {
  const ov = o ?? {};
  const photoFile = ov.photo_file ?? null;
  const video = ov.video_id ? { id: ov.video_id, title: ov.video_title || "YouTube" } : base.video;
  const views: View[] = [];
  if ((base.hasPhoto || photoFile) && ov.photo !== false) views.push("photo");
  if (video && ov.video !== false) views.push("video");
  if (ov.anim3d !== false) views.push("3d");
  const initial = ov.default && views.includes(ov.default) ? ov.default : views[0] ?? null;
  return { views, initial, photoFile, video: views.includes("video") ? video : null };
}

export const fileUrl = (id: string) => `/api/v1/media/files/${encodeURIComponent(id)}`;

let overridesP: Promise<Record<string, MediaOverride>> | null = null;
/** Public, cached per page load; a failure means "no overrides" (bundled behaviour), never an error for the learner. */
export function loadOverrides(force = false): Promise<Record<string, MediaOverride>> {
  if (force) overridesP = null;
  return (overridesP ??= fetch("/api/v1/media/overrides", { cache: "no-store" })
    .then((r) => (r.ok ? r.json() : { overrides: {} }))
    .then((j: { overrides?: Record<string, MediaOverride> }) => j.overrides ?? {})
    .catch(() => ({})));
}

function cookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const m = document.cookie.split("; ").find((c) => c.startsWith(name + "="));
  return m ? decodeURIComponent(m.slice(name.length + 1)) : undefined;
}

export type AdminResult<T> = { ok: true; data: T } | { ok: false; status: number; code: string };
export async function adminCall<T = unknown>(method: "GET" | "POST" | "PUT" | "DELETE", path: string, body?: unknown): Promise<AdminResult<T>> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") { headers["Content-Type"] = "application/json"; const c = cookie("csrftoken"); if (c) headers["X-CSRFToken"] = c; }
  try {
    const r = await fetch("/api/v1" + path, { method, headers, body: method === "GET" ? undefined : JSON.stringify(body ?? {}), credentials: "same-origin", cache: "no-store" });
    const text = await r.text();
    const j = text ? JSON.parse(text) : {};
    return r.ok ? { ok: true, data: j as T } : { ok: false, status: r.status, code: (j as { code?: string }).code ?? "error" };
  } catch { return { ok: false, status: 0, code: "network_error" }; }
}

/** File → base64 (no data: prefix) for the upload route. */
export function fileToBase64(f: Blob): Promise<string> {
  return new Promise((res, rej) => { const r = new FileReader(); r.onload = () => res(String(r.result).split(",")[1] ?? ""); r.onerror = () => rej(new Error("read")); r.readAsDataURL(f); });
}

/** Re-encodes an image to webp ≤ maxSide px so phone photos fit the 300 KB upload limit. Falls back to the original when it already fits. */
export async function shrinkImage(f: File, maxSide = 900, maxBytes = 280_000): Promise<Blob> {
  if (f.size <= maxBytes && /^image\/(png|jpeg|webp)$/.test(f.type)) return f;
  const bmp = await createImageBitmap(f);
  const k = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas"); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
  c.getContext("2d")!.drawImage(bmp, 0, 0, c.width, c.height);
  for (const q of [0.85, 0.7, 0.55, 0.4]) {
    const b: Blob | null = await new Promise((r) => c.toBlob(r, "image/webp", q));
    if (b && b.size <= maxBytes) return b;
  }
  throw new Error("too_large");
}

/** Accepts a bare 11-char id or any common YouTube URL form; returns the id or null. */
export function parseYouTubeId(s: string): string | null {
  const t = s.trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(t)) return t;
  try {
    const u = new URL(t);
    const h = u.hostname.replace(/^www\.|^m\./, "");
    let id: string | null = null;
    if (h === "youtu.be") id = u.pathname.slice(1).split("/")[0];
    else if (h === "youtube.com" || h === "youtube-nocookie.com") id = u.searchParams.get("v") ?? (/^\/(embed|shorts)\/([^/]+)/.exec(u.pathname)?.[2] ?? null);
    return id && /^[A-Za-z0-9_-]{11}$/.test(id) ? id : null;
  } catch { return null; }
}

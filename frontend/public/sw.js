// Offline shell for static assets ONLY. Health data must never be cached by the service worker:
// anything under /api/ and every non-GET request goes straight to the network and is never stored.
const CACHE = "vitaforge-static-v5";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const req = e.request; const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;
  if (!(url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/vendor/") || url.pathname.startsWith("/exercise-media/") || url.pathname === "/icon.svg")) return;
  e.respondWith(caches.open(CACHE).then(async (c) => {
    // Code and the media index go network-first so a deploy is never masked by a stale cached viewer; hashed/binary assets stay cache-first.
    const fresh = url.pathname.endsWith(".js") || url.pathname.endsWith("index.json");
    if (fresh) { try { const res = await fetch(req); if (res.ok) c.put(req, res.clone()); return res; } catch { const hit = await c.match(req); if (hit) return hit; throw new Error("offline"); } }
    const hit = await c.match(req); if (hit) return hit;
    const res = await fetch(req); if (res.ok) c.put(req, res.clone()); return res;
  }));
});

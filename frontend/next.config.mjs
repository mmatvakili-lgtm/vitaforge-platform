/** The browser talks to the SAME origin; Next proxies /api/v1/* to the Django backend, so the HttpOnly session cookie and the
 *  CSRF cookie (ADR-0009) are first-party and no CORS is needed. */
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default {
  reactStrictMode: true,
  // Headers that cannot break the app. A full script-src CSP needs per-request nonces and a real-browser check: tracked as a release-candidate item.
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "same-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
        { key: "Content-Security-Policy", value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" },
      ],
    }];
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }];
  },
};

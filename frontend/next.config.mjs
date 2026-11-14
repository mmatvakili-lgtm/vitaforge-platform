/** The browser talks to the SAME origin; Next proxies /api/v1/* to the Django backend, so the HttpOnly session cookie and the
 *  CSRF cookie (ADR-0009) are first-party and no CORS is needed. */
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const dev = process.env.NODE_ENV !== "production";
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self'${dev ? " ws: wss:" : ""}`,
  "manifest-src 'self'",
  "worker-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

export default {
  reactStrictMode: true,
  // CSP without nonces: scripts only from our own origin plus Next's inline bootstrap ('unsafe-inline'); everything else (third-party scripts,
  // framing, plugins, cross-origin requests) is blocked. A nonce-based policy would force every page to render dynamically: tracked as hardening.
  // Verified by the real-browser e2e (no CSP violations on the register -> Telegram -> onboarding journey).
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "same-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
        { key: "Content-Security-Policy", value: csp },
      ],
    }];
  },
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }];
  },
};

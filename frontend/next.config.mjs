/** The browser talks to the SAME origin; Next proxies /api/v1/* to the Django backend, so the HttpOnly session cookie and the
 *  CSRF cookie (ADR-0009) are first-party and no CORS is needed. */
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default {
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }];
  },
};

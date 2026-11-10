# VitaForge Frontend (Next.js 15, App Router, TypeScript)

Persian (RTL) + English (LTR), responsive. Built directly on the OpenAPI contract (56 operations).

## Structure
- `src/lib/api/generated.ts` — GENERATED types + operation table (`python3 tools/gen_frontend_api.py`; a backend test fails if stale).
- `src/lib/api/client.ts` — typed client: cookie session (HttpOnly `sessionid`), `X-CSRFToken` double-submit, no Bearer.
- `src/lib/{i18n,onboarding,plan-view}.ts` — pure logic (tested with Node's runner).
- `src/lib/plan-view.ts` — the only place deciding if a plan may be shown: only ALLOW / ALLOW_WITH_MODIFICATION / RESTRICT with a plan object. All other Safety Core outcomes show the decision, never a plan.
- `src/app/[locale]/*` — home, login, register, verify, onboarding (basics → goal → schedule → equipment → consent → screening → finish), plan.
- `next.config.mjs` rewrites `/api/v1/*` to `BACKEND_URL` (default `http://127.0.0.1:8000`) so cookies stay same-origin.

- `src/app/[locale]/nutrition` — weekly nutrition (estimate → preferences → week tabs, meals, shopping list, budget). `src/lib/nutrition.ts` decides what may be shown: days only for status OK; NEEDS_CONTENT/REFER/BLOCKED always show an explanation.
- `src/app/[locale]/exercises/[id]` — exercise detail.

## Not built (no contract support)
Food/recipe browsing and food exclusions by id (needs `/foods`, `/recipes`, still deferred), nutrition meal logging UI, password-reset UI, sessions list, profile edit, workout logging, progress, subscription, admin screens; phone sign-up; onboarding steps 5–14; a screening-question list endpoint (ids are fixed in `onboarding.ts`, checked against the backend by a test).

## Run (Windows PowerShell)
```
cd D:\vitaforge-platform\backend ; python manage.py runserver 127.0.0.1:8000      # set VITAFORGE_DEV_CONTENT=true + DJANGO_DEBUG=true for demo exercises
cd D:\vitaforge-platform\frontend ; npm install ; npm run typecheck ; npm test ; npm run dev
```
Open http://localhost:3000. Without dev content the Safety Core correctly refuses to build plans (no reviewed exercises).

## Tests
`npm test` (pure logic). `node --experimental-strip-types scripts/e2e-flow.ts http://127.0.0.1:8000/api/v1` runs the real client through register → plan against a running API.

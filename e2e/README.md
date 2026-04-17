# End-to-end tests (Playwright)

Browser-level regression suite for GovDoc SecureFlow. Exercises the full
document workflow against a running stack (web + api + sqlite) through a
real Chromium instance.

## What is covered

`govdoc.spec.ts` runs ten sequential steps that mirror the demo script:

1. Landing page renders
2. Role switcher (header `<select>`)
3. Intake clerk upload happy path
4. Review queue lists documents
5. Approve routing
6. Request consultation with a custom body (BUG-006 regression)
7. Resolve consultation (BUG-005 regression)
8. Close document
9. No TypeError on the consultation page (BUG-001 regression)
10. Consultant role (BUG-004 regression)

Each test starts with `POST /api/v1/demo/reset` so the suite is
self-contained and ordering independent.

## Prerequisites

- `make up` — full Docker stack running
- API reachable at `http://localhost:8000` (healthcheck `/healthz`)
- Web reachable at `http://localhost:3000`
- Valid Model Studio credentials in `.env` (uploads call live AI)

## Running

Preferred entry point (asserts the stack is up first):

```bash
make test-e2e
```

Or directly from the repo root:

```bash
npx playwright test
```

Playwright config (`playwright.config.ts`) sets `baseURL` to
`http://172.17.0.1:3000` — the Docker bridge gateway — so the test runs
from inside another container or from the host. If you run the stack
with host networking, override it:

```bash
PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test
```

(or edit `playwright.config.ts` directly).

## CI scope

`make ci` does **not** run Playwright — E2E is kept separate per
`docs/govdoc_test_plan.md` §4.1. `make test` only runs the Python
`unit`, `contract`, and `mock_integration` markers.

# End-to-end tests (placeholder)

Pass 3 adds this directory as a **structural placeholder** for a future Playwright (or similar) suite.

- **Not run** in `make ci` or `make test` today.
- **`make test-e2e`** currently exits with a clear “not implemented” message until browser automation is added.

Planned shape (later passes):

- Run against `make up` (web + api) or ephemeral compose.
- Smoke critical flows: role switcher, intake list, document detail, upload happy path.

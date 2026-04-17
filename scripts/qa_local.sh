#!/usr/bin/env bash
# Local smoke checks against running web + api (honest HTTP status checks only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_URL="${API_URL:-http://127.0.0.1:${APP_PORT:-8000}}"
WEB_URL="${WEB_URL:-http://127.0.0.1:${WEB_PORT:-3000}}"
ROLE_HEADER="X-GovDoc-Role: intake_clerk"

fail() {
  echo "qa_local: $*" >&2
  exit 1
}

check_http() {
  local name="$1" url="$2" expect="${3:-200}"; shift "$(( $# >= 3 ? 3 : $# ))"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$url" "$@" || true)"
  if [[ "$code" != "$expect" ]]; then
    fail "$name expected HTTP $expect from $url, got $code"
  fi
  echo "qa_local: $name OK ($url -> $code)"
}

echo "=== Local QA Smoke Checks ==="

# 1. API health
check_http "1. API health" "$API_URL/healthz"

# 2. API ready
check_http "2. API ready" "$API_URL/readyz"

# 3. Web responds
check_http "3. Web responds" "$WEB_URL/"

# 4. Meta roles
check_http "4. Meta roles" "$API_URL/api/v1/meta/roles"

# 5. Meta departments
check_http "5. Meta departments" "$API_URL/api/v1/meta/departments"

# 6. Documents list with role
check_http "6. Documents list" "$API_URL/api/v1/documents/" 200 "-H" "$ROLE_HEADER"

# 7. Demo scenarios
check_http "7. Demo scenarios" "$API_URL/api/v1/demo/scenarios"

echo ""
echo "=== All QA checks passed ==="

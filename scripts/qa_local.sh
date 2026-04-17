#!/usr/bin/env bash
# Local smoke checks against running web + api (honest HTTP status checks only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_URL="${API_URL:-http://127.0.0.1:8000}"
WEB_URL="${WEB_URL:-http://127.0.0.1:3000}"

fail() {
  echo "qa_local: $*" >&2
  exit 1
}

check_http() {
  local name="$1" url="$2" expect="${3:-200}"
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$url" || true)"
  if [[ "$code" != "$expect" ]]; then
    fail "$name expected HTTP $expect from $url, got $code"
  fi
  echo "qa_local: $name OK ($url -> $code)"
}

check_http "api liveness" "$API_URL/health"
check_http "api readiness (DB)" "$API_URL/health/ready"
check_http "web home" "$WEB_URL/"

echo "qa_local: all checks passed."

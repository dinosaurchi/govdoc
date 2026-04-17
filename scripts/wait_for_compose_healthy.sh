#!/usr/bin/env bash
# Wait until api + web report healthy (fallback if `docker compose up --wait` is unavailable).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

max_attempts="${GOVDOC_HEALTH_WAIT_ATTEMPTS:-60}"
sleep_s="${GOVDOC_HEALTH_SLEEP_S:-2}"

for i in $(seq 1 "$max_attempts"); do
  api_id="$(docker compose ps -q api 2>/dev/null || true)"
  web_id="$(docker compose ps -q web 2>/dev/null || true)"
  if [[ -z "$api_id" || -z "$web_id" ]]; then
    echo "wait_for_compose_healthy: waiting for containers (attempt $i/$max_attempts)"
    sleep "$sleep_s"
    continue
  fi
  api_health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$api_id" 2>/dev/null || echo unknown)"
  web_health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$web_id" 2>/dev/null || echo unknown)"

  if [[ "$api_health" == "healthy" && "$web_health" == "healthy" ]]; then
    echo "wait_for_compose_healthy: api=$api_health web=$web_health"
    exit 0
  fi
  echo "wait_for_compose_healthy: attempt $i/$max_attempts api=$api_health web=$web_health"
  sleep "$sleep_s"
done

echo "wait_for_compose_healthy: timed out waiting for healthy services" >&2
docker compose ps >&2
exit 1

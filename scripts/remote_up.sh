#!/usr/bin/env bash
# Build images locally, upload to remote host, deploy with docker compose.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REMOTE_HOST="${REMOTE_HOST:-47.84.131.45}"
REMOTE_USER="${REMOTE_USER:-root}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/opt/govdoc}"
SSH_KEY="${GOVDOC_SSH_KEY:-$HOME/.ssh/alibaba-govdoc.pem}"
SSH_OPTS="-o StrictHostKeyChecking=no -i $SSH_KEY"
RSYNC_OPTS="-avz --progress -e \"ssh $SSH_OPTS\""

echo "=== remote_up: building images ==="
bash "$ROOT/scripts/remote_package.sh"

echo "=== remote_up: finding image tar ==="
tar_path="$(ls -t deploy/artifacts/govdoc-secureflow-images-*.tar 2>/dev/null | head -1)"
if [[ -z "$tar_path" ]]; then
  echo "remote_up: no image tar found in deploy/artifacts/" >&2
  exit 1
fi
echo "  Image: $tar_path ($(du -h "$tar_path" | cut -f1))"

echo "=== remote_up: creating remote directory ==="
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_APP_DIR}/{data,bundle,artifacts}"

echo "=== remote_up: uploading image tar ==="
rsync -avz --progress -e "ssh $SSH_OPTS" "$tar_path" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/artifacts/"

echo "=== remote_up: uploading docker-compose.yml ==="
rsync -avz --progress -e "ssh $SSH_OPTS" docker-compose.yml "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/"

echo "=== remote_up: uploading .env ==="
rsync -avz --progress -e "ssh $SSH_OPTS" .env "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/"

echo "=== remote_up: uploading data/ ==="
rsync -avz --delete --progress -e "ssh $SSH_OPTS" "$ROOT/data/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/data/"

echo "=== remote_up: loading images on remote ==="
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "docker load -i ${REMOTE_APP_DIR}/artifacts/$(basename "$tar_path")"

echo "=== remote_up: stopping old containers ==="
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_APP_DIR} && docker compose down --remove-orphans || true"

echo "=== remote_up: starting containers ==="
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_APP_DIR} && docker compose up -d --no-build"

echo "=== remote_up: waiting for healthy services ==="
max_attempts=60
sleep_s=5
for i in $(seq 1 "$max_attempts"); do
  api_health="$(ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" \
    "docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \$(docker compose -f ${REMOTE_APP_DIR}/docker-compose.yml ps -q api 2>/dev/null) 2>/dev/null || echo unknown")"
  web_health="$(ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" \
    "docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \$(docker compose -f ${REMOTE_APP_DIR}/docker-compose.yml ps -q web 2>/dev/null) 2>/dev/null || echo unknown")"

  if [[ "$api_health" == "healthy" && "$web_health" == "healthy" ]]; then
    echo "  api=$api_health web=$web_health"
    break
  fi
  echo "  attempt $i/$max_attempts api=$api_health web=$web_health"
  sleep "$sleep_s"
done

if [[ "${api_health:-unknown}" != "healthy" || "${web_health:-unknown}" != "healthy" ]]; then
  echo "remote_up: timed out waiting for healthy services" >&2
  ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_APP_DIR} && docker compose ps" >&2
  exit 1
fi

echo "=== remote_up: seeding demo workflow ==="
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_APP_DIR} && docker compose exec -T api python -m app.seed_demo"

echo "=== remote_up: verifying seeded demo state ==="
ssh $SSH_OPTS "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_APP_DIR} && docker compose exec -T api python - <<'PY'
import json
import urllib.request

def get_json(url: str):
    req = urllib.request.Request(url, headers={'X-GovDoc-Role': 'supervisor'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))

scenarios = get_json('http://127.0.0.1:8000/api/v1/demo/scenarios')
docs = get_json('http://127.0.0.1:8000/api/v1/documents/')
stats = get_json('http://127.0.0.1:8000/api/v1/dashboard/stats')

if len(scenarios) < 4:
    raise SystemExit(f'Expected at least 4 demo scenarios, got {len(scenarios)}')
if len(docs) < 4:
    raise SystemExit(f'Expected at least 4 documents, got {len(docs)}')

statuses = {doc['status'] for doc in docs}
required = {'closed', 'under_review', 'in_consultation', 'out_of_scope'}
missing = required - statuses
if missing:
    raise SystemExit(f'Missing required seeded statuses: {sorted(missing)}')

print('demo scenarios:', len(scenarios))
print('document statuses:', sorted(statuses))
print('dashboard:', stats)
PY"

echo "=== remote_up: deploy complete! ==="
echo "  API: http://${REMOTE_HOST}:${APP_PORT:-8000}"
echo "  Web: http://${REMOTE_HOST}:${WEB_PORT:-3000}"

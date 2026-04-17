#!/usr/bin/env bash
# Full remote flow contract: package images, then stop — remote ssh/rsync apply is TODO.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${REMOTE_HOST:-}" || -z "${REMOTE_USER:-}" || -z "${REMOTE_APP_DIR:-}" ]]; then
  echo "remote_up: set REMOTE_HOST, REMOTE_USER, and REMOTE_APP_DIR (see README)." >&2
  echo "  These name the target VPS path used in the documented rsync contract." >&2
  exit 1
fi

bash "$ROOT/scripts/remote_package.sh"

echo "" >&2
echo "remote_up: REMOTE DEPLOY APPLY NOT IMPLEMENTED (honest failure after successful packaging)." >&2
echo "  Example transfer (you run manually on a plain Linux VPS):" >&2
echo "    rsync -avz deploy/bundle/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/bundle/" >&2
echo "    rsync -avz deploy/artifacts/*.tar ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_APP_DIR}/artifacts/" >&2
echo "  On remote: docker load -i ... && docker compose -f bundle/docker-compose.yml up -d" >&2
echo "  Optional hook GOVDOC_REMOTE_APPLY=1 will remain failing until scripts/remote_apply.sh exists." >&2

if [[ "${GOVDOC_REMOTE_APPLY:-0}" == "1" ]]; then
  echo "remote_up: GOVDOC_REMOTE_APPLY=1 set but remote_apply.sh is still TODO." >&2
fi
exit 1

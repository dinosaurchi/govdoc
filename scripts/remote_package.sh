#!/usr/bin/env bash
# Build docker images and export a single tar bundle + compose/Dockerfile copies (exits 0).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f docker-compose.yml ]]; then
  echo "remote_package: docker-compose.yml not found at repo root" >&2
  exit 1
fi

mkdir -p deploy/artifacts deploy/bundle

echo "remote_package: building images..."
docker compose build

echo "remote_package: exporting image bundle..."
images="$(docker compose config --images)"
if [[ -z "$images" ]]; then
  echo "remote_package: no images from docker compose config --images" >&2
  exit 1
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
tar_path="deploy/artifacts/govdoc-secureflow-images-${ts}.tar"
# shellcheck disable=SC2086
docker save -o "$tar_path" $images
echo "remote_package: saved $tar_path"

cp docker-compose.yml deploy/bundle/docker-compose.yml
cp deploy/Dockerfile.api deploy/bundle/
cp deploy/Dockerfile.web deploy/bundle/
echo "$ts" > deploy/bundle/BUNDLE_VERSION.txt

{
  echo "bundle_time_utc=$ts"
  echo "images:"
  docker compose config --images
  echo "image_tar=$tar_path"
} > deploy/bundle/MANIFEST.txt

echo "remote_package: manifest deploy/bundle/MANIFEST.txt"
echo "remote_package: done."

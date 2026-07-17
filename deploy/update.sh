#!/usr/bin/env sh
set -eu

MANIFEST="${SG_GATEWAY_RELEASE_MANIFEST:-release-manifest.json}"

echo "SG-Gateway updater"
echo "Manifest: $MANIFEST"

if [ ! -f "$MANIFEST" ]; then
  echo "Release manifest not found: $MANIFEST" >&2
  exit 1
fi

VERSION="$(python3 -c "import json; print(json.load(open('$MANIFEST', encoding='utf-8'))['version'])")"
PANEL_IMAGE="$(python3 -c "import json; print(json.load(open('$MANIFEST', encoding='utf-8'))['images']['panel'])")"
XRAY_IMAGE="$(python3 -c "import json; print(json.load(open('$MANIFEST', encoding='utf-8'))['images']['xray'])")"

echo "Version: $VERSION"
echo "Panel image: $PANEL_IMAGE"
echo "Xray image: $XRAY_IMAGE"

docker compose config >/dev/null
docker compose pull || true

cat <<'NEXT'
Next safe update flow:
  1. Create panel backup.
  2. Pull pinned images from release manifest.
  3. Start new panel.
  4. Check /health.
  5. Keep previous version available for rollback.
NEXT
#!/usr/bin/env sh
set -eu

echo "SG-Gateway updater"
echo "This MVP updater only validates compose and pulls configured images."

docker compose config >/dev/null
docker compose pull || true

cat <<'NEXT'
Next safe update flow:
  1. Create panel backup.
  2. Pull pinned images.
  3. Start new panel.
  4. Check /health.
  5. Keep previous version available for rollback.
NEXT
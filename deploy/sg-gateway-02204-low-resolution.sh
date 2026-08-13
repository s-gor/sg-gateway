#!/usr/bin/env bash
set -Eeuo pipefail

PREFIX="${SG_GATEWAY_PREFIX:-/opt/sg-gateway}"
TARGET="$PREFIX/app/web/static/sg-mobile-sidebar-v1.css"
SOURCE="$PREFIX/app/web/static/sg-low-resolution-v1.css"
START='/* SG_LOW_RESOLUTION_V1_START */'
END='/* SG_LOW_RESOLUTION_V1_END */'

[[ -f "$TARGET" ]] || { echo "Missing: $TARGET" >&2; exit 1; }
[[ -f "$SOURCE" ]] || { echo "Missing: $SOURCE" >&2; exit 1; }

python3 - "$TARGET" "$SOURCE" "$START" "$END" <<'PY'
from pathlib import Path
import sys

target, source, start, end = map(str, sys.argv[1:])
p = Path(target)
text = p.read_text(encoding="utf-8")
while start in text and end in text:
    a = text.index(start)
    b = text.index(end, a) + len(end)
    text = text[:a].rstrip() + "\n" + text[b:].lstrip("\n")
payload = Path(source).read_text(encoding="utf-8").strip()
p.write_text(text.rstrip() + "\n\n" + start + "\n" + payload + "\n" + end + "\n", encoding="utf-8")
PY

grep -Fq "$START" "$TARGET"
grep -Fq '@media (min-width: 981px) and (max-width: 1366px)' "$TARGET"
echo "[PASS] SG-Gateway 022.04 Low-resolution Desktop applied."

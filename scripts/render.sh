#!/usr/bin/env bash
# HTMLをPNGに書き出す: render.sh <input.html> <output.png> <width> <height>
set -euo pipefail
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
mkdir -p "$(dirname "$2")"
"$CHROME" --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size="$3,$4" --screenshot="$(realpath -m "$2")" "file://$(realpath "$1")" 2>/dev/null
echo "rendered $2"

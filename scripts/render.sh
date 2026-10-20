#!/usr/bin/env bash
# HTMLをPNGに書き出す: render.sh <input.html> <output.png> <width> <height>
# ヘッドレスChromeは下端が切れることがあるので、縦に余白をとって描画してから指定サイズに切り出す。
set -euo pipefail
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
out="$(realpath -m "$2")"; tmp="${out%.png}.tmp.png"
mkdir -p "$(dirname "$out")"
"$CHROME" --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size="$3,$(( $4 + 200 ))" --screenshot="$tmp" "file://$(realpath "$1")" 2>/dev/null
ffmpeg -y -loglevel error -i "$tmp" -vf "crop=$3:$4:0:0" "$out"
rm -f "$tmp"
echo "rendered $2"

#!/usr/bin/env bash
# HTMLをPNGに書き出す: render.sh <input.html> <output.png> <width> <height>
# ヘッドレスChromeは下端が切れることがあるので、縦に余白をとって描画してから指定サイズに切り出す。
# TRANSPARENT=1 を付けると背景を透明にする（ミニキャラ用）。input には ?pose=... のようなクエリを付けてもよい。
set -euo pipefail
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
out="$(realpath -m "$2")"; tmp="${out%.png}.tmp.png"
mkdir -p "$(dirname "$out")"
bgflag=""; [ "${TRANSPARENT:-0}" = 1 ] && bgflag="--headless=new --default-background-color=00000000"
src="$1"; q=""; case "$src" in *\?*) q="?${src#*\?}"; src="${src%%\?*}";; esac
"$CHROME" $( [ -z "$bgflag" ] && echo --headless ) --no-sandbox --disable-gpu --hide-scrollbars $bgflag \
  --window-size="$3,$(( $4 + 200 ))" --screenshot="$tmp" "file://$(realpath "$src")$q" 2>/dev/null
ffmpeg -y -loglevel error -i "$tmp" -vf "crop=$3:$4:0:0" "$out"
rm -f "$tmp"
echo "rendered $2"

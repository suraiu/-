#!/usr/bin/env bash
# スライドPNGを縦型mp4にする: make_reel.sh <slides_dir> <秒数のカンマ区切り 例 2,6,10,7,5> <output.mp4>
set -euo pipefail
dir="$1"; IFS=',' read -ra durs <<< "$2"; out="$3"
list="$(mktemp)"
i=0
for f in $(ls "$dir"/*.png | sort); do
  echo "file '$(realpath "$f")'" >> "$list"
  echo "duration ${durs[$i]:-3}" >> "$list"
  last="$f"; i=$((i+1))
done
echo "file '$(realpath "$last")'" >> "$list"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$list" \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p" \
  -r 30 -c:v libx264 "$out"
rm -f "$list"
echo "made $out"

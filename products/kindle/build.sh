#!/usr/bin/env bash
# Kindle本を書き出す: build.sh  → 各巻に manuscript.epub（KDP提出用）と manuscript.docx を作る
set -euo pipefail
cd "$(dirname "$0")"
for d in vol1_email vol2_minutes vol3_notices; do
  title="$(grep -m1 '^# ' "$d/manuscript.md" | sed 's/^# //')"
  pandoc "$d/manuscript.md" -o "$d/manuscript.epub" --toc --toc-depth=2 \
    --css _style/kindle.css --epub-cover-image "$d/cover.png" \
    --metadata title="$title" --metadata author="スライム国" --metadata lang=ja
  pandoc "$d/manuscript.md" -o "$d/manuscript.docx" --toc --toc-depth=2 \
    --reference-doc _style/reference.docx --metadata title="$title"
  echo "built $d"
done

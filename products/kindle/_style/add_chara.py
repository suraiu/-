"""章の見出し（# ）の直後に、ミニキャラ「ぷるの」の画像を差しこんだMarkdownを標準出力に書く。
使い方: python3 add_chara.py manuscript.md > 一時ファイル.md
"""
import sys, os

CHARA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chara")
ROTATION = ["normal", "idea", "ok", "cheer"]


def pick(title, i):
    if any(k in title for k in ("注意", "安全", "個人情報", "気をつけ", "困った")):
        return "caution"
    if "はじめに" in title or "この本について" in title:
        return "normal"
    if any(k in title for k in ("おわりに", "あとがき")):
        return "cheer"
    if any(k in title for k in ("付録", "まとめ", "早見", "逆引き")):
        return "ok"
    if any(k in title for k in ("基本", "コツ")):
        return "idea"
    return ROTATION[i % len(ROTATION)]


out, n, in_code = [], 0, False
for line in open(sys.argv[1], encoding="utf-8"):
    out.append(line)
    if line.startswith("```"):
        in_code = not in_code
    if not in_code and line.startswith("# "):
        pose = pick(line, n)
        n += 1
        out.append(f'\n![ぷるの]({CHARA}/puruno_{pose}.png){{.chara}}\n\n')
sys.stdout.write("".join(out))

#!/usr/bin/env python3
"""note記事のMarkdownから、スマホでコピペして投稿するための「貼り付けページ」(HTML)を作る。

使い方:
  python3 scripts/note_build.py products/note/002_xxx
  → products/note/002_xxx/paste.html を作る（Artifactとして公開して、スマホで開く）

記事フォルダの中身:
  article.md   本文。先頭の「# タイトル」がタイトルになる。
               画像・GIFは ![説明](images/x.png) を1行で書く。
               有料部分の始まりに <!-- paid --> を1行で書く。
  meta.json    任意。{"price": 300, "hashtags": ["#AI", ...], "header": "header.png"}

ページの作り:
  文章のかたまりごとに「コピー」ボタン（見出し・太字・リスト・引用・コードを保ったままコピー）。
  画像はページに表示し、長押しで保存してnoteに挿入する。
  有料エリアの線を入れる位置と、コードだけを別にコピーするボタンも出す。
"""
import base64
import html
import json
import mimetypes
import re
import subprocess
import sys
from pathlib import Path

IMG_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$")
PAID = "<!-- paid -->"


def md_to_html(md: str) -> str:
    out = subprocess.run(
        ["pandoc", "-f", "markdown+hard_line_breaks-implicit_figures", "-t", "html", "--no-highlight", "--wrap=none"],
        input=md.encode("utf-8"), capture_output=True, check=True,
    )
    return out.stdout.decode("utf-8")


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def split_blocks(md: str):
    """本文を「文章」「画像」「有料の線」のかたまりに分ける。コードブロックの中は分けない。"""
    blocks, buf, in_code = [], [], False

    def flush():
        text = "".join(buf).strip("\n")
        if text.strip():
            blocks.append(("text", text))
        buf.clear()

    for line in md.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if not in_code and line.strip() == PAID:
            flush()
            blocks.append(("paid", None))
            continue
        if not in_code and line.startswith("## "):
            flush()  # 大見出しごとにコピーの単位を分ける
        m = None if in_code else IMG_LINE.match(line.strip())
        if m:
            flush()
            blocks.append(("image", (m.group(1), m.group(2))))
            continue
        buf.append(line)
    flush()
    return blocks


def count_chars(md: str) -> int:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    text = re.sub(r"[#*>`\-]|<!--.*?-->", "", text)
    return len(re.sub(r"\s", "", text))


def build(folder: Path) -> Path:
    md = (folder / "article.md").read_text(encoding="utf-8")
    meta = {}
    if (folder / "meta.json").exists():
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))

    title = meta.get("title")
    lines = md.splitlines(keepends=True)
    if lines and lines[0].startswith("# "):
        title = title or lines[0][2:].strip()
        md = "".join(lines[1:])
    title = title or folder.name

    parts = md.split(PAID)
    free_chars = count_chars(parts[0])
    paid_chars = count_chars(parts[1]) if len(parts) > 1 else 0

    cards, n_text, n_img, n_code = [], 0, 0, 0
    header = folder / meta.get("header", "header.png")
    if header.exists():
        cards.append(f'''<section class="card img">
  <p class="step">見出し画像（記事の一番上に設定）</p>
  <img src="{data_uri(header)}" alt="見出し画像">
  <p class="hint">長押しで保存 → noteの「見出し画像」に設定</p>
</section>''')

    for kind, val in split_blocks(md):
        if kind == "paid":
            cards.append('''<section class="paid">
  <p><strong>ここで有料エリアの線を入れる</strong></p>
  <p>noteの「公開設定」で「有料」を選び、この位置に「ここから有料エリア」の線を移動します。</p>
</section>''')
        elif kind == "image":
            alt, src = val
            path = (folder / src).resolve()
            n_img += 1
            if not path.exists():
                cards.append(f'<section class="card img missing"><p>画像が見つかりません：{html.escape(src)}</p></section>')
                continue
            kind_label = "GIF（動く画像）" if path.suffix.lower() == ".gif" else "画像"
            cards.append(f'''<section class="card img">
  <p class="step">{kind_label} {n_img}：{html.escape(alt)}</p>
  <img src="{data_uri(path)}" alt="{html.escape(alt)}">
  <p class="hint">長押しで保存 → noteの「＋」→「画像」で、この位置に挿入</p>
</section>''')
        else:
            n_text += 1
            body = md_to_html(val)
            codes = re.findall(r"<pre><code[^>]*>(.*?)</code></pre>", body, re.S)
            code_buttons = ""
            for c in codes:
                n_code += 1
                code_buttons += (f'<button class="copy code" data-plain="{html.escape(html.unescape(c), quote=True)}">'
                                 f'コード{n_code}だけコピー</button>')
            cards.append(f'''<section class="card text">
  <div class="bar"><span class="step">文章 {n_text}</span><button class="copy rich">この部分をコピー</button></div>
  <div class="body">{body}</div>
  {f'<div class="codes"><p class="hint">コードは、noteの「＋」→「コード」に貼ると見やすくなります</p>{code_buttons}</div>' if code_buttons else ''}
</section>''')

    tags = " ".join(meta.get("hashtags", []))
    price = meta.get("price")
    summary = f"文字数：約{free_chars + paid_chars:,}字（無料 {free_chars:,}字／有料 {paid_chars:,}字）"
    page = TEMPLATE.format(
        title=html.escape(title),
        title_attr=html.escape(title, quote=True),
        summary=summary,
        price=f"価格：{price}円" if price else "価格：未設定",
        tags_html=(f'<button class="copy plain" data-plain="{html.escape(tags, quote=True)}">ハッシュタグをコピー</button>'
                   f'<p class="tags">{html.escape(tags)}</p>') if tags else "",
        cards="\n".join(cards),
    )
    out = folder / "paste.html"
    out.write_text(page, encoding="utf-8")
    print(f"{out}  {summary}  画像{n_img}  コード{n_code}  {out.stat().st_size / 1e6:.1f}MB")
    return out


TEMPLATE = """<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&family=Noto+Sans+JP:wght@400;700&display=swap">
<style>
/* 1列の作業台：上から順にコピーしてnoteに貼るだけ。スライムの水色をアクセントに */
:root {{
  --bg: #F3F7FA; --surface: #FFFFFF; --fg: #13202B; --muted: #5B6B78;
  --line: #D5E1EA; --accent: #0284C7; --accent-fg: #FFFFFF; --paid: #B45309; --paid-bg: #FEF3C7;
  --display: "M PLUS Rounded 1c", "Hiragino Maru Gothic ProN", "Noto Sans JP", sans-serif;
  --body: "Noto Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0D1720; --surface: #15232F; --fg: #E6EEF4; --muted: #93A6B5;
  --line: #27394A; --accent: #38BDF8; --accent-fg: #062033; --paid: #FBBF24; --paid-bg: #3A2A0A; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0D1720; --surface: #15232F; --fg: #E6EEF4; --muted: #93A6B5;
  --line: #27394A; --accent: #38BDF8; --accent-fg: #062033; --paid: #FBBF24; --paid-bg: #3A2A0A; color-scheme: dark; }}
body {{ background: var(--bg); color: var(--fg); font: 16px/1.8 var(--body);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 20px 48px; }}
main {{ max-width: 680px; margin: 0 auto; display: grid; gap: 14px; }}
header h1 {{ font: 800 1.45rem/1.4 var(--display); margin: 0 0 6px; text-wrap: balance; }}
header .meta {{ color: var(--muted); font-size: .85rem; margin: 0; }}
.how {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; font-size: .9rem; }}
.how ol {{ margin: 0; padding-left: 1.3em; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; min-width: 0; }}
.bar {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }}
.step {{ font: 700 .78rem/1.4 var(--display); letter-spacing: .04em; color: var(--accent); margin: 0; }}
.body {{ min-width: 0; }}
.body h2 {{ font-size: 1.2rem; line-height: 1.5; margin: 1em 0 .4em; text-wrap: balance; }}
.body h3 {{ font-size: 1.05rem; margin: .9em 0 .3em; }}
.body p {{ margin: 0 0 .9em; }}
.body blockquote {{ margin: 0 0 .9em; padding-left: 12px; border-left: 3px solid var(--line); color: var(--muted); }}
.body pre {{ overflow-x: auto; background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 10px; font: .8rem/1.6 var(--mono); }}
.body a {{ color: var(--accent); word-break: break-all; }}
.img img {{ display: block; width: 100%; height: auto; border-radius: 6px; margin: 6px 0; }}
.hint {{ color: var(--muted); font-size: .8rem; margin: 4px 0 0; }}
.codes {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; border-top: 1px dashed var(--line); padding-top: 8px; }}
.codes .hint {{ flex-basis: 100%; margin: 0; }}
button.copy {{ font: 700 .85rem/1 var(--display); border: 0; border-radius: 999px; padding: 10px 16px; cursor: pointer;
  background: var(--accent); color: var(--accent-fg); }}
button.copy.code, button.copy.plain {{ background: transparent; color: var(--accent); border: 1.5px solid var(--accent); }}
button.copy.done {{ background: var(--fg); color: var(--bg); border-color: var(--fg); }}
button:focus-visible {{ outline: 3px solid var(--accent); outline-offset: 2px; }}
.paid {{ background: var(--paid-bg); color: var(--paid); border: 2px dashed var(--paid); border-radius: 10px; padding: 12px 14px; font-size: .9rem; }}
.paid p {{ margin: 0 0 4px; }}
.tags {{ font-size: .85rem; color: var(--muted); margin: 6px 0 0; word-break: break-all; }}
.missing {{ color: var(--paid); }}
</style>
<main>
  <header>
    <h1>{title}</h1>
    <p class="meta">{summary}　{price}</p>
  </header>
  <section class="how">
    <ol>
      <li>noteで「投稿」→「テキスト」を開き、タイトル欄に貼る：<button class="copy plain" data-plain="{title_attr}">タイトルをコピー</button></li>
      <li>上から順に「この部分をコピー」を押して、noteの本文に貼る。</li>
      <li>画像の所では、長押しで保存して、noteの「＋」から同じ位置に挿入する。</li>
      <li>黄色い枠の位置に、有料エリアの線を入れる。</li>
    </ol>
    {tags_html}
  </section>
{cards}
</main>
<script>
function mark(btn, ok) {{
  const t = btn.textContent;
  btn.textContent = ok ? "コピーしました" : "長押しで選んでコピーしてください";
  btn.classList.add("done");
  setTimeout(() => {{ btn.textContent = t; btn.classList.remove("done"); }}, 1800);
}}
function selectNode(node) {{
  const r = document.createRange(); r.selectNodeContents(node);
  const s = getSelection(); s.removeAllRanges(); s.addRange(r);
}}
document.addEventListener("click", async (e) => {{
  const btn = e.target.closest("button.copy");
  if (!btn) return;
  if (btn.classList.contains("rich")) {{
    const body = btn.closest(".card").querySelector(".body");
    try {{
      const item = new ClipboardItem({{
        "text/html": new Blob([body.innerHTML], {{ type: "text/html" }}),
        "text/plain": new Blob([body.innerText], {{ type: "text/plain" }}),
      }});
      await navigator.clipboard.write([item]);
      mark(btn, true);
    }} catch (_) {{
      try {{ await navigator.clipboard.writeText(body.innerText); mark(btn, true); }}
      catch (_) {{ selectNode(body); mark(btn, false); }}
    }}
  }} else {{
    try {{ await navigator.clipboard.writeText(btn.dataset.plain); mark(btn, true); }}
    catch (_) {{ mark(btn, false); }}
  }}
}});
</script>
"""

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        build(Path(arg))

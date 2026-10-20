#!/usr/bin/env python3
"""Threads にテキストを1本投稿する（Python 3 標準ライブラリのみ）。

使い方:
  python3 scripts/post_threads.py "本文"            # 本文を引数で
  python3 scripts/post_threads.py --file post.txt   # 本文をファイルから
  python3 scripts/post_threads.py --dry-run "本文"  # 送信しない（環境変数も不要）

環境変数（値はログ・ファイルに出さない）:
  THREADS_ACCESS_TOKEN  threads_content_publish 権限つきのユーザーアクセストークン
  THREADS_USER_ID       Threads のユーザーID（数字）

API（WebSearch の抜粋で確認。公式ページ本文は開けていない）:
  1) POST https://graph.threads.net/v1.0/{user-id}/threads
       media_type=TEXT, text=本文 → {"id": コンテナID}
  2) （待つ。Meta は約30秒待つことを勧めているとされる）
  3) POST https://graph.threads.net/v1.0/{user-id}/threads_publish
       creation_id=コンテナID → {"id": 投稿ID}
要確認:
  - ホスト名：抜粋の例は graph.threads.net。graph.threads.com と書かれた版もある。
    環境変数 THREADS_API_BASE で差し替えられるようにした。
  - access_token をフォームの本文（POST body）で送っている。URLに入れないため。
    Authorization: Bearer ヘッダーでも通るかは未確認。
  - 文字数上限は500字（絵文字は UTF-8 のバイト数で数えるという抜粋あり）。ここでは
    「文字数（コードポイント）」と「絵文字をバイト数で数えた値」の両方で500以内を確認する。
  - 返信（reply_to_id）は、抜粋レベルの情報で実装。
  - 投稿上限は24時間で250件（公式の抜粋）。
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sns_common as c  # noqa: E402

API_BASE = os.environ.get("THREADS_API_BASE", "https://graph.threads.net/v1.0").rstrip("/")
MAX_CHARS = 500
DEFAULT_WAIT_SEC = 30


def threads_length(text):
    """(コードポイント数, 絵文字をUTF-8バイト数で数えた長さ) を返す。"""
    plain = len(text)
    weighted = 0
    for ch in text:
        cp = ord(ch)
        # 絵文字のおおまかな範囲（近似。要確認）
        is_emoji = (cp >= 0x1F000 or 0x2600 <= cp <= 0x27BF or 0xFE00 <= cp <= 0xFE0F
                    or ch == "‍")
        weighted += len(ch.encode("utf-8")) if is_emoji else 1
    return plain, weighted


def check_text(text):
    if not text.strip():
        raise ValueError("本文が空です")
    plain, weighted = threads_length(text)
    if plain > MAX_CHARS:
        raise ValueError("Threads の上限 {} 字を超えています（{} 字）".format(MAX_CHARS, plain))
    if weighted > MAX_CHARS:
        raise ValueError("絵文字をバイト数で数えると {} になり、上限 {} を超えます（要確認の数え方）".format(
            weighted, MAX_CHARS))
    return plain, weighted


def load_credentials():
    env = c.require_env(["THREADS_ACCESS_TOKEN", "THREADS_USER_ID"], "Threads への投稿")
    c.register_secret(env["THREADS_ACCESS_TOKEN"])
    if not env["THREADS_USER_ID"].isdigit():
        raise c.MissingEnvError("THREADS_USER_ID は数字のIDを設定してください（値は表示しません）")
    return env["THREADS_ACCESS_TOKEN"], env["THREADS_USER_ID"]


def post(text, *, reply_to_id=None, wait_sec=DEFAULT_WAIT_SEC, creds=None):
    """投稿して、公開された投稿ID（文字列）を返す。"""
    check_text(text)
    token, user_id = creds or load_credentials()

    form = {"media_type": "TEXT", "text": text, "access_token": token}
    if reply_to_id:
        form["reply_to_id"] = reply_to_id  # 要確認
    _, res = c.http_request("POST", "{}/{}/threads".format(API_BASE, user_id), form=form)
    container_id = res.get("id")
    if not container_id:
        raise c.PostError(c.redact("コンテナIDが返ってきませんでした: {}".format(res)))

    if wait_sec > 0:
        time.sleep(wait_sec)

    try:
        _, res = c.http_request(
            "POST", "{}/{}/threads_publish".format(API_BASE, user_id),
            form={"creation_id": container_id, "access_token": token},
        )
    except c.PostError as e:
        e.maybe_posted = e.maybe_sent  # 公開の段階で届いたか不明なら、出し直さない
        raise
    post_id = res.get("id")
    if not post_id:
        err = c.PostError(c.redact("公開に失敗しました（投稿IDが返ってこない）: {}".format(res)))
        err.maybe_posted = True  # 2xx で ID が無い＝公開されたか分からない
        raise err
    return str(post_id)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Threads にテキスト投稿する")
    ap.add_argument("text", nargs="?", help="本文")
    ap.add_argument("--file", help="本文を読むファイル（UTF-8）")
    ap.add_argument("--reply-to", help="返信先の Threads 投稿ID（要確認）")
    ap.add_argument("--wait", type=int, default=DEFAULT_WAIT_SEC,
                    help="コンテナ作成から公開までの待ち秒数（既定 30）")
    ap.add_argument("--dry-run", action="store_true", help="送信せず内容と文字数だけ表示")
    args = ap.parse_args(argv)

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read().strip()
    elif args.text is not None:
        text = args.text
    else:
        c.fail("本文を引数か --file で指定してください")

    try:
        plain, weighted = check_text(text)
    except ValueError as e:
        c.fail(str(e))

    if args.dry_run:
        has_env = all(os.environ.get(n) for n in ("THREADS_ACCESS_TOKEN", "THREADS_USER_ID"))
        print("[dry-run] Threads に送信しません")
        print("  文字数: {} / {}（絵文字バイト換算 {}）".format(plain, MAX_CHARS, weighted))
        print("  環境変数: {}".format("設定あり" if has_env else "未設定（本番では止まります）"))
        if args.reply_to:
            print("  返信先ID: {}".format(args.reply_to))
        print("---- 本文 ----")
        print(text)
        return 0

    try:
        post_id = post(text, reply_to_id=args.reply_to, wait_sec=args.wait)
    except c.MissingEnvError as e:
        c.fail(str(e), code=2)
    except c.PostError as e:
        c.fail("Threads への投稿に失敗: {}".format(e))
    print("Threads に投稿しました。投稿ID: {}".format(post_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())

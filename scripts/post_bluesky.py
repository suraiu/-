#!/usr/bin/env python3
"""Bluesky にテキストを1本投稿する（Python 3 標準ライブラリのみ）。

使い方:
  python3 scripts/post_bluesky.py "本文"
  python3 scripts/post_bluesky.py --file post.txt
  python3 scripts/post_bluesky.py --dry-run "本文"   # 送信しない（環境変数も不要）

環境変数（値はログ・ファイルに出さない）:
  BLUESKY_HANDLE        例: slime-no-chishiki.bsky.social
  BLUESKY_APP_PASSWORD  アプリパスワード（ふだんのログインパスワードは使わない）

API（WebSearch の抜粋で確認。公式ページ本文は開けていない）:
  1) POST https://bsky.social/xrpc/com.atproto.server.createSession
       {"identifier": ハンドル, "password": アプリパスワード} → accessJwt, did
  2) POST https://bsky.social/xrpc/com.atproto.repo.createRecord
       Authorization: Bearer accessJwt
       {"repo": did, "collection": "app.bsky.feed.post",
        "record": {"$type": "app.bsky.feed.post", "text": 本文, "createdAt": ISO8601(UTC)}}
       → {"uri": ..., "cid": ...}
  本文の上限は300書記素（graphemes）、さらに3,000バイト（抜粋で確認）。
要確認:
  - 書記素の数え方：標準ライブラリに書記素分割が無いので近似（sns_common.count_graphemes）。
    日本語・英数字は正確。複雑な絵文字は誤差が出るかもしれない。
  - "langs": ["ja"] を付けている（任意項目とされる）。
  - URL・ハッシュタグは facets を付けないとリンクにならない。この会社の投稿は本文にリンクを
    入れない方針なので facets は未実装。
  - createSession を投稿のたびに呼ぶとレート制限にかかる可能性がある、という抜粋あり。
    post_queue.py では1回の実行で1回だけログインして使い回す。
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sns_common as c  # noqa: E402

PDS = os.environ.get("BLUESKY_PDS", "https://bsky.social").rstrip("/")
MAX_GRAPHEMES = 300
MAX_BYTES = 3000


def check_text(text):
    if not text.strip():
        raise ValueError("本文が空です")
    g = c.count_graphemes(text)
    b = len(text.encode("utf-8"))
    if g > MAX_GRAPHEMES:
        raise ValueError("Bluesky の上限 {} 字を超えています（{} 字）".format(MAX_GRAPHEMES, g))
    if b > MAX_BYTES:
        raise ValueError("Bluesky の上限 {} バイトを超えています（{} バイト）".format(MAX_BYTES, b))
    return g, b


class Session:
    """ログイン済みセッション。accessJwt はメモリにだけ持つ。"""

    def __init__(self, access_jwt, did):
        self._jwt = access_jwt
        self.did = did

    def auth_header(self):
        return {"Authorization": "Bearer " + self._jwt}

    def __repr__(self):
        return "Session(did={}, jwt=***)".format(self.did)


def login():
    env = c.require_env(["BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"], "Bluesky への投稿")
    c.register_secret(env["BLUESKY_APP_PASSWORD"])
    _, res = c.http_request(
        "POST", PDS + "/xrpc/com.atproto.server.createSession",
        json_body={"identifier": env["BLUESKY_HANDLE"], "password": env["BLUESKY_APP_PASSWORD"]},
    )
    jwt, did = res.get("accessJwt"), res.get("did")
    if not jwt or not did:
        raise c.PostError("ログインに失敗しました（accessJwt / did が返ってこない）")
    c.register_secret(jwt)
    if res.get("refreshJwt"):
        c.register_secret(res["refreshJwt"])
    return Session(jwt, did)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def post(text, *, session=None, reply=None):
    """投稿して {"uri":..., "cid":...} を返す。

    reply: {"root": {"uri","cid"}, "parent": {"uri","cid"}}（返信にする場合）
    """
    check_text(text)
    session = session or login()
    record = {"$type": "app.bsky.feed.post", "text": text, "createdAt": now_iso(), "langs": ["ja"]}
    if reply:
        record["reply"] = reply
    try:
        _, res = c.http_request(
            "POST", PDS + "/xrpc/com.atproto.repo.createRecord",
            json_body={"repo": session.did, "collection": "app.bsky.feed.post", "record": record},
            headers=session.auth_header(),
        )
    except c.PostError as e:
        e.maybe_posted = e.maybe_sent  # 届いたか不明なら、出し直さない
        raise
    if not res.get("uri"):
        err = c.PostError(c.redact("投稿に失敗しました（uri が返ってこない）: {}".format(res)))
        err.maybe_posted = True
        raise err
    return {"uri": res["uri"], "cid": res.get("cid", "")}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bluesky にテキスト投稿する")
    ap.add_argument("text", nargs="?", help="本文")
    ap.add_argument("--file", help="本文を読むファイル（UTF-8）")
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
        g, b = check_text(text)
    except ValueError as e:
        c.fail(str(e))

    if args.dry_run:
        has_env = all(os.environ.get(n) for n in ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"))
        print("[dry-run] Bluesky に送信しません")
        print("  文字数: {} / {}（{} バイト / {}）".format(g, MAX_GRAPHEMES, b, MAX_BYTES))
        print("  環境変数: {}".format("設定あり" if has_env else "未設定（本番では止まります）"))
        print("---- 本文 ----")
        print(text)
        return 0

    try:
        res = post(text)
    except c.MissingEnvError as e:
        c.fail(str(e), code=2)
    except c.PostError as e:
        c.fail("Bluesky への投稿に失敗: {}".format(e))
    print("Bluesky に投稿しました。URI: {}".format(res["uri"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

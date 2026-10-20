#!/usr/bin/env python3
"""X（旧Twitter）にテキストを1本投稿する（Python 3 標準ライブラリのみ）。

使い方:
  python3 scripts/post_x.py "本文"
  python3 scripts/post_x.py --file post.txt
  python3 scripts/post_x.py --reply-to 1234567890 "返信の本文"
  python3 scripts/post_x.py --dry-run "本文"   # 送信しない（環境変数も不要）

環境変数（値はログ・ファイルに出さない）:
  X_API_KEY              API Key（Consumer Key）
  X_API_SECRET           API Key Secret（Consumer Secret）
  X_ACCESS_TOKEN         Access Token（投稿するアカウントのもの。Read and Write 権限で作る）
  X_ACCESS_TOKEN_SECRET  Access Token Secret
  任意: X_API_BASE（既定 https://api.x.com。動作確認でローカルの仮サーバーに向けるため）

API（WebSearch の抜粋で確認。公式ページ本文は開けていない）:
  POST https://api.x.com/2/tweets
    Authorization: OAuth ...（OAuth 1.0a ユーザーコンテキスト、HMAC-SHA1）
    {"text": 本文}  返信なら {"text": 本文, "reply": {"in_reply_to_tweet_id": "返信先ID"}}
    → {"data": {"id": "投稿ID", "text": ...}}
  本文は JSON なので、署名の材料には入れない（OAuth の署名に入るのはクエリとフォームの値だけ）。

文字数（Xの数え方。twitter-text v3 の設定の抜粋で確認）:
  - 次の範囲の文字は1、それ以外（日本語・全角・絵文字など）は2として数え、合計280以下。
    U+0000–U+10FF、U+2000–U+200D、U+2010–U+201F、U+2032–U+2037
  - URL は長さに関係なく23。
  - 絵文字は、ZWJ や肌の色・異体字セレクタでつながっていても全体で2（ここでは近似）。
  - 先に NFC 正規化してから数える。

料金（業者の記事の抜粋。2026-04 から）：URL を含む投稿は1本あたりの料金が高い。
  そのため、この単体スクリプトは URL を含む本文を --allow-url なしでは送らない。
  post_queue.py は URL を含む X 投稿をスキップする。
"""

import argparse
import base64
import hashlib
import hmac
import os
import re
import secrets
import sys
import time
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sns_common as c  # noqa: E402

API_BASE = os.environ.get("X_API_BASE", "https://api.x.com").rstrip("/")
ENV_NAMES = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
MAX_WEIGHT = 280
URL_WEIGHT = 23
_LIGHT_RANGES = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))

# ---- OAuth 1.0a ---------------------------------------------------------


def pct(s):
    """RFC 3986 のパーセントエンコード（英数字と - . _ ~ 以外はすべて %XX）。"""
    return urllib.parse.quote(str(s), safe="~")


def signature_base_string(method, url, params):
    """署名のもとになる文字列。params はクエリ・フォーム・oauth_* をまとめた dict。"""
    p = urllib.parse.urlsplit(url)
    base_url = urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, "", ""))
    pairs = sorted((pct(k), pct(v)) for k, v in params.items())
    param_str = "&".join("{}={}".format(k, v) for k, v in pairs)
    return "&".join([method.upper(), pct(base_url), pct(param_str)])


def oauth_signature(method, url, params, consumer_secret, token_secret):
    key = "{}&{}".format(pct(consumer_secret), pct(token_secret)).encode("utf-8")
    base = signature_base_string(method, url, params).encode("utf-8")
    return base64.b64encode(hmac.new(key, base, hashlib.sha1).digest()).decode("ascii")


def oauth_header(method, url, creds, *, extra_params=None, nonce=None, timestamp=None):
    """Authorization ヘッダーの値を作る。extra_params はクエリ・フォームの値（JSON本文は入れない）。"""
    oauth = {
        "oauth_consumer_key": creds["X_API_KEY"],
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(timestamp if timestamp is not None else int(time.time())),
        "oauth_token": creds["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    params = dict(extra_params or {})
    params.update(oauth)
    oauth["oauth_signature"] = oauth_signature(method, url, params, creds["X_API_SECRET"],
                                               creds["X_ACCESS_TOKEN_SECRET"])
    return "OAuth " + ", ".join('{}="{}"'.format(pct(k), pct(v)) for k, v in sorted(oauth.items()))


# ---- 文字数 -------------------------------------------------------------

# http(s):// で始まるもの、www. で始まるもの、よくあるドメイン（example.com / example.co.jp など）
_URL_PATH = r"[A-Za-z0-9\-._~:/?#\[\]@!$&'*+,;=%]"
_URL_RE = re.compile(
    r"(?:https?://|www\.)" + _URL_PATH + "+"
    r"|(?<![A-Za-z0-9@._\-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+"
    r"(?:com|net|org|jp|io|ai|co|me|ly|app|dev|info|biz|tv|us|uk|be|to|gl|link|site|xyz|shop|blog|page)"
    r"(?![A-Za-z0-9_\-])(?:/" + _URL_PATH + "*)?",
    re.I,
)


def find_urls(text):
    return _URL_RE.findall(unicodedata.normalize("NFC", text))


def _char_weight(cp):
    for lo, hi in _LIGHT_RANGES:
        if lo <= cp <= hi:
            return 1
    return 2


def x_length(text):
    """Xの数え方での長さ（全角2・半角1・URL 23）。"""
    text = unicodedata.normalize("NFC", text)
    total = 0
    pos = 0
    for m in _URL_RE.finditer(text):
        total += _weight_plain(text[pos:m.start()]) + URL_WEIGHT
        pos = m.end()
    return total + _weight_plain(text[pos:])


def _weight_plain(text):
    total = 0
    join_next = False
    ri_pending = False
    for ch in text:
        cp = ord(ch)
        if ch == "‍":  # ZWJ：次の文字は前の絵文字の一部
            join_next = True
            continue
        if 0xFE00 <= cp <= 0xFE0F or 0x1F3FB <= cp <= 0x1F3FF or 0xE0020 <= cp <= 0xE007F or cp == 0x20E3:
            continue  # 異体字セレクタ・肌の色・タグ文字・キーキャップ
        if join_next:
            join_next = False
            continue
        if 0x1F1E6 <= cp <= 0x1F1FF:  # 国旗は地域指示記号2つで1つの絵文字
            if ri_pending:
                ri_pending = False
                continue
            ri_pending = True
            total += 2
            continue
        ri_pending = False
        total += _char_weight(cp)
    return total


def check_text(text, allow_url=True):
    """(Xの数え方での長さ, URLの数) を返す。上限を超えたら ValueError。"""
    if not text.strip():
        raise ValueError("本文が空です")
    n = x_length(text)
    if n > MAX_WEIGHT:
        raise ValueError("X の上限 {} を超えています（Xの数え方で {}。全角は2、URLは23）".format(MAX_WEIGHT, n))
    urls = find_urls(text)
    if urls and not allow_url:
        raise ValueError("URL を含んでいます（URL つきの投稿は料金が高いので送りません。"
                         "URL はプロフィールや返信に置く運用です。どうしても送るなら --allow-url）")
    return n, len(urls)


# ---- 投稿 ---------------------------------------------------------------


def load_credentials():
    env = c.require_env(ENV_NAMES, "X への投稿")
    for name in ENV_NAMES:
        c.register_secret(env[name])
    return env


def post(text, *, reply_to_id=None, creds=None, allow_url=True):
    """投稿して、投稿ID（文字列）を返す。"""
    check_text(text, allow_url=allow_url)
    creds = creds or load_credentials()
    url = API_BASE + "/2/tweets"
    body = {"text": text}
    if reply_to_id:
        body["reply"] = {"in_reply_to_tweet_id": str(reply_to_id)}
    try:
        _, res = c.http_request("POST", url, json_body=body,
                                headers={"Authorization": oauth_header("POST", url, creds)})
    except c.PostError as e:
        e.maybe_posted = e.maybe_sent  # 届いたか不明なら、出し直さない
        raise
    post_id = (res.get("data") or {}).get("id") if isinstance(res, dict) else None
    if not post_id:
        err = c.PostError(c.redact("投稿に失敗しました（投稿IDが返ってこない）: {}".format(res)))
        err.maybe_posted = True  # 2xx で ID が無い＝投稿されたか分からない
        raise err
    return str(post_id)


def main(argv=None):
    ap = argparse.ArgumentParser(description="X にテキスト投稿する")
    ap.add_argument("text", nargs="?", help="本文")
    ap.add_argument("--file", help="本文を読むファイル（UTF-8）")
    ap.add_argument("--reply-to", help="返信先の X 投稿ID")
    ap.add_argument("--allow-url", action="store_true", help="URL を含む本文でも送る（料金が高い）")
    ap.add_argument("--dry-run", action="store_true", help="送信せず内容と文字数だけ表示")
    args = ap.parse_args(argv)

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read().strip()
    elif args.text is not None:
        text = args.text
    else:
        c.fail("本文を引数か --file で指定してください")
    if args.reply_to and not args.reply_to.isdigit():
        c.fail("--reply-to は数字の投稿IDを指定してください")

    try:
        n, n_url = check_text(text, allow_url=args.allow_url or args.dry_run)
    except ValueError as e:
        c.fail(str(e))

    if args.dry_run:
        has_env = all(os.environ.get(name) for name in ENV_NAMES)
        print("[dry-run] X に送信しません")
        print("  文字数（Xの数え方。全角2・半角1・URL23）: {} / {}".format(n, MAX_WEIGHT))
        if n_url:
            print("  警告: URL を {} 個含みます。URL つきの投稿は料金が高く、キューからは出しません".format(n_url))
        print("  環境変数: {}".format("設定あり" if has_env else "未設定（本番では止まります）"))
        if args.reply_to:
            print("  返信先ID: {}".format(args.reply_to))
        print("---- 本文 ----")
        print(text)
        return 0

    try:
        post_id = post(text, reply_to_id=args.reply_to, allow_url=args.allow_url)
    except c.MissingEnvError as e:
        c.fail(str(e), code=2)
    except c.PostError as e:
        c.fail("X への投稿に失敗: {}".format(e))
    print("X に投稿しました。投稿ID: {}".format(post_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())

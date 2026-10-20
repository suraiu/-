"""投稿スクリプトの共通部品（Python 3 標準ライブラリのみ）。

ルール：
- トークン・パスワードの値は、ログにもファイルにも絶対に出さない。
  エラー表示は必ず redact() を通してから出す。
- 環境変数が無いときは MissingEnvError を出して止まる。
"""

import http.client
import json
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "slime-koku-poster/1.0 (+stdlib urllib)"
TIMEOUT_SEC = 30

# redact() で伏せ字にする値（プロセス内のメモリだけに置く。ファイルには書かない）
_SECRETS = set()


class MissingEnvError(Exception):
    """必要な環境変数が設定されていない。"""


class PostError(Exception):
    """API呼び出しに失敗した（メッセージは redact 済み）。

    maybe_sent: リクエストは相手に届いたかもしれない（タイムアウト・接続切れ・5xx）。
                投稿の最後の段階でこれが True のときは「投稿されたか不明」として扱い、
                自動で出し直さない（二重投稿を防ぐため）。
    maybe_posted: 投稿スクリプトが「投稿されたかもしれない」と判断したとき True。
    """

    def __init__(self, msg, maybe_sent=False):
        super().__init__(msg)
        self.maybe_sent = maybe_sent
        self.maybe_posted = False


def register_secret(value):
    if value:
        _SECRETS.add(value)


def redact(text):
    """秘密の値が文字列に含まれていたら伏せ字にする。"""
    text = str(text)
    for s in _SECRETS:
        if s and s in text:
            text = text.replace(s, "***")
    return text


def require_env(names, purpose):
    """環境変数をまとめて読む。足りなければ、何が足りないかだけを言って止める（値は出さない）。"""
    values = {}
    missing = []
    for name in names:
        v = os.environ.get(name, "").strip()
        if not v:
            missing.append(name)
        else:
            values[name] = v
    if missing:
        raise MissingEnvError(
            "{} に必要な環境変数が設定されていません: {}\n"
            "  例) export {}=...   （値はこの画面やファイルに貼らず、環境の設定に登録してください）".format(
                purpose, ", ".join(missing), missing[0]
            )
        )
    return values


def http_request(method, url, *, form=None, json_body=None, headers=None):
    """HTTPリクエストを送り、(status, dict) を返す。失敗時は PostError（redact 済み）。

    秘密の値は URL に入れない（URLはプロキシやエラーメッセージに残りやすいため）。
    """
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    elif json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, _parse_json(body)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise PostError(redact("HTTP {} {}: {}".format(e.code, _safe_url(url), body[:500])),
                        maybe_sent=e.code >= 500)
    except urllib.error.URLError as e:
        # 接続前の失敗（名前解決・接続拒否）もここに来るが、区別できないので「届いたかも」とみなす
        raise PostError(redact("接続できませんでした {}: {}".format(_safe_url(url), e.reason)),
                        maybe_sent=True)
    except TimeoutError:
        raise PostError("タイムアウトしました: {}".format(_safe_url(url)), maybe_sent=True)
    except (http.client.HTTPException, OSError) as e:
        # 接続切れ（RemoteDisconnected・ConnectionResetError など）。素の例外で落ちないようにする
        raise PostError(redact("通信が途中で切れました {}: {}".format(_safe_url(url), type(e).__name__)),
                        maybe_sent=True)


def _parse_json(body):
    if not body:
        return {}
    try:
        return json.loads(body)
    except ValueError:
        return {"_raw": body[:500]}


def _safe_url(url):
    """クエリ文字列を落としたURL（念のため。秘密はもともとURLに入れていない）。"""
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, "", ""))


# ---- 文字数 -------------------------------------------------------------

_ZWJ = "‍"


def count_graphemes(text):
    """書記素（見た目の1文字）のおおよその数。

    標準ライブラリには書記素クラスタ分割（Intl.Segmenter 相当）が無いので近似：
    - 結合文字（Mn/Me/Mc）・異体字セレクタ・肌の色の修飾子は前の文字に含める
    - ZWJ でつながった絵文字は1文字
    - 国旗（地域指示記号2つ）は1文字
    日本語・英数字・ふつうの記号は正確に数えられる。複雑な絵文字は誤差が出る可能性あり（要確認）。
    """
    count = 0
    join_next = False
    ri_pending = False  # 地域指示記号の1つ目を見た直後
    for ch in text:
        cp = ord(ch)
        cat = unicodedata.category(ch)
        if ch == _ZWJ:
            join_next = True
            continue
        if cat in ("Mn", "Me", "Mc") or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF \
                or 0x1F3FB <= cp <= 0x1F3FF or 0xE0020 <= cp <= 0xE007F:
            continue
        if join_next:
            join_next = False
            continue
        if 0x1F1E6 <= cp <= 0x1F1FF:
            if ri_pending:
                ri_pending = False
                continue
            ri_pending = True
            count += 1
            continue
        ri_pending = False
        if ch == "\r":
            continue  # \r\n は1文字として数える
        count += 1
    return count


def fail(msg, code=1):
    print("エラー: " + redact(msg), file=sys.stderr)
    sys.exit(code)

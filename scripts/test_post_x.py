#!/usr/bin/env python3
"""post_x.py と post_queue.py の X 対応のテスト（標準ライブラリのみ。実際の API には送らない）。

  python3 scripts/test_post_x.py

- OAuth 1.0a 署名：X の公式ドキュメント「Creating a signature」の例の値で、
  例に載っている署名 hCtSmYh+iHYCEqBWrE7C7hYmtUk= になるか。
- 文字数：全角2・半角1・URL 23。
- ローカルの仮サーバー（127.0.0.1）を相手に、投稿・返信・二重投稿防止・1日の上限・URL のスキップ・
  「投稿されたか不明」で出し直さないこと・秘密が出力やファイルに出ないこと。
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import post_queue  # noqa: E402
import post_x  # noqa: E402
import sns_common as c  # noqa: E402

FAKE = {
    "X_API_KEY": "fake-consumer-key-AAA",
    "X_API_SECRET": "fake-consumer-secret-BBB",
    "X_ACCESS_TOKEN": "fake-access-token-CCC",
    "X_ACCESS_TOKEN_SECRET": "fake-token-secret-DDD",
}


class MockX:
    """POST /2/tweets を受けて、署名を検算し、投稿IDを返す仮サーバー。"""

    def __init__(self):
        self.requests = []
        self.next_id = 1000
        self.fail_with = None  # 500 などを返したいとき
        mock = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
                auth = self.headers.get("Authorization", "")
                ok = mock.verify(auth, "http://127.0.0.1:{}{}".format(mock.port, self.path))
                mock.requests.append({"path": self.path, "body": body, "sig_ok": ok})
                if not ok:
                    return self._send(401, {"title": "Unauthorized"})
                if mock.fail_with:
                    # エラー本文に秘密が混ざった場合も伏せ字になるかを見る
                    return self._send(mock.fail_with, {"detail": "oops " + FAKE["X_API_SECRET"]})
                mock.next_id += 1
                self._send(201, {"data": {"id": str(mock.next_id), "text": body["text"]}})

            def _send(self, code, obj):
                data = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def verify(self, auth, url):
        if not auth.startswith("OAuth "):
            return False
        params = {}
        for part in auth[6:].split(", "):
            k, v = part.split("=", 1)
            params[urllib.parse.unquote(k)] = urllib.parse.unquote(v.strip('"'))
        sig = params.pop("oauth_signature", None)
        if params.get("oauth_consumer_key") != FAKE["X_API_KEY"] or params.get("oauth_token") != FAKE["X_ACCESS_TOKEN"]:
            return False
        want = post_x.oauth_signature("POST", url, params, FAKE["X_API_SECRET"], FAKE["X_ACCESS_TOKEN_SECRET"])
        return sig == want

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class TestSignature(unittest.TestCase):
    def test_official_example(self):
        # X 公式「Creating a signature」の例（WebSearch の抜粋で確認した値）
        params = {
            "status": "Hello Ladies + Gentlemen, a signed OAuth request!",
            "include_entities": "true",
            "oauth_consumer_key": "xvz1evFS4wEEPTGEFPHBog",
            "oauth_nonce": "kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg",
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": "1318622958",
            "oauth_token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
            "oauth_version": "1.0",
        }
        url = "https://api.twitter.com/1.1/statuses/update.json"
        base = post_x.signature_base_string("POST", url, params)
        self.assertTrue(base.startswith(
            "POST&https%3A%2F%2Fapi.twitter.com%2F1.1%2Fstatuses%2Fupdate.json&include_entities%3Dtrue%26"))
        self.assertIn("status%3DHello%2520Ladies%2520%252B%2520Gentlemen%252C%2520a%2520signed%2520OAuth%2520request%2521",
                      base)
        sig = post_x.oauth_signature("POST", url, params, "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
                                     "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE")
        self.assertEqual(sig, "hCtSmYh+iHYCEqBWrE7C7hYmtUk=")

    def test_header_uses_given_nonce(self):
        h = post_x.oauth_header("POST", "https://api.x.com/2/tweets", FAKE, nonce="abc", timestamp=1)
        self.assertTrue(h.startswith("OAuth "))
        self.assertIn('oauth_nonce="abc"', h)
        self.assertIn('oauth_signature="', h)


class TestLength(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(post_x.x_length("abc"), 3)
        self.assertEqual(post_x.x_length("あいう"), 6)
        self.assertEqual(post_x.x_length("ＡＢ"), 4)            # 全角英字は2
        self.assertEqual(post_x.x_length("“a”"), 3)             # U+201C/D は1
        self.assertEqual(post_x.x_length("https://example.com/very/long/path?x=1"), 23)
        self.assertEqual(post_x.x_length("見て https://a.co"), 2 * 2 + 1 + 23)
        self.assertEqual(post_x.x_length("👍"), 2)
        self.assertEqual(post_x.x_length("👨‍👩‍👧"), 2)
        self.assertEqual(post_x.x_length("🇯🇵"), 2)

    def test_limits(self):
        post_x.check_text("あ" * 140)
        with self.assertRaises(ValueError):
            post_x.check_text("あ" * 141)
        post_x.check_text("a" * 280)
        with self.assertRaises(ValueError):
            post_x.check_text("a" * 281)
        with self.assertRaises(ValueError):
            post_x.check_text("見て example.com", allow_url=False)
        self.assertEqual(post_x.check_text("見て example.com")[1], 1)


class TestWithMockServer(unittest.TestCase):
    def setUp(self):
        self.mock = MockX()
        self.tmp = tempfile.mkdtemp()
        self._saved = (post_x.API_BASE, post_queue.CONFIG, post_queue.POSTED, dict(os.environ))
        post_x.API_BASE = "http://127.0.0.1:{}".format(self.mock.port)
        post_queue.CONFIG = os.path.join(self.tmp, "config.md")
        post_queue.POSTED = os.path.join(self.tmp, "posted.md")
        with open(post_queue.CONFIG, "w", encoding="utf-8") as f:
            f.write("AUTO_POST: true\nTIMEZONE: Asia/Tokyo\nX_DAILY_LIMIT: 5\n")
        with open(post_queue.POSTED, "w", encoding="utf-8") as f:
            f.write("| 日付 | SNS | ネタ | 本文の冒頭 |\n|---|---|---|---|\n")
        os.environ.update(FAKE)
        self.qdir = os.path.join(self.tmp, "2026-11-01")
        os.makedirs(self.qdir)
        self.qpath = os.path.join(self.qdir, "queue.json")

    def tearDown(self):
        post_x.API_BASE, post_queue.CONFIG, post_queue.POSTED, env = self._saved
        os.environ.clear()
        os.environ.update(env)
        self.mock.close()
        shutil.rmtree(self.tmp)

    def write_queue(self, posts):
        with open(self.qpath, "w", encoding="utf-8") as f:
            json.dump({"date": "2026-11-01", "posts": posts}, f, ensure_ascii=False)

    def run_queue(self, now="2026-11-01T13:00:00+09:00"):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = post_queue.main(["--queue", self.qpath, "--now", now, "--date", "2026-11-01"])
            except SystemExit as e:
                code = e.code
        return code, out.getvalue() + err.getvalue()

    def state(self):
        with open(os.path.join(self.qdir, "queue_state.json"), encoding="utf-8") as f:
            return json.load(f)["posted"]

    def assert_no_secrets(self, text):
        for v in FAKE.values():
            self.assertNotIn(v, text)

    def test_single_post_and_reply(self):
        creds = post_x.load_credentials()
        pid = post_x.post("こんにちは", creds=creds)
        rid = post_x.post("返信です", reply_to_id=pid, creds=creds)
        self.assertNotEqual(pid, rid)
        self.assertTrue(all(r["sig_ok"] for r in self.mock.requests))
        self.assertEqual(self.mock.requests[0]["path"], "/2/tweets")
        self.assertEqual(self.mock.requests[0]["body"], {"text": "こんにちは"})
        self.assertEqual(self.mock.requests[1]["body"]["reply"], {"in_reply_to_tweet_id": pid})

    def test_queue_post_reply_dedup_limit_url(self):
        def p(i, h, **kw):
            d = {"id": i, "sns": "x", "scheduled_at": "2026-11-01T{}:00+09:00".format(h), "qc": "ok",
                 "neta": "テスト", "text": "本文 " + i}
            d.update(kw)
            return d
        self.write_queue([
            p("x1", "08:00"),
            p("x1-ans", "08:30", reply_to="x1"),
            p("x-url", "09:00", text="詳しくは https://example.com/a"),
            p("x3", "10:00"), p("x4", "10:30"), p("x5", "11:00"), p("x6", "11:30"),
            p("x-late", "14:00"),
            {"id": "t1", "sns": "threads", "scheduled_at": "2026-11-01T23:00:00+09:00", "qc": "ok", "text": "後で"},
        ])
        code, out = self.run_queue()
        self.assertEqual(code, 0, out)
        st = self.state()
        self.assertEqual(sorted(st), ["x1", "x1-ans", "x3", "x4", "x5"])           # 上限5本
        self.assertTrue(all(r["status"] == "posted" for r in st.values()))
        self.assertIn("URL を含む X 投稿なのでスキップ", out)
        self.assertIn("x6: X の1日の上限 5 本", out)
        bodies = [r["body"] for r in self.mock.requests]
        self.assertEqual(len(bodies), 5)
        self.assertTrue(all(r["sig_ok"] for r in self.mock.requests))
        self.assertEqual(bodies[1]["reply"], {"in_reply_to_tweet_id": st["x1"]["post_id"]})  # 返信
        self.assertFalse(any("example.com" in b["text"] for b in bodies))
        with open(post_queue.POSTED, encoding="utf-8") as f:
            self.assertEqual(f.read().count("| X |"), 5)

        # 2回目：二重投稿しない。上限に達しているので x-late も出さない
        code, out2 = self.run_queue(now="2026-11-01T15:00:00+09:00")
        self.assertEqual(len(self.mock.requests), 5, out2)
        self.assertIn("x-late: X の1日の上限 5 本", out2)

        # 上限を上げると、残りが出る（すでに出したものは出さない）
        with open(post_queue.CONFIG, "w", encoding="utf-8") as f:
            f.write("AUTO_POST: true\nTIMEZONE: Asia/Tokyo\nX_DAILY_LIMIT: 7\n")
        code, out3 = self.run_queue(now="2026-11-01T15:00:00+09:00")
        self.assertEqual(len(self.mock.requests), 7, out3)
        self.assertIn("x6", self.state())
        self.assertIn("x-late", self.state())
        self.assertNotIn("x-url", self.state())

        files = ""
        for name in os.listdir(self.qdir):
            with open(os.path.join(self.qdir, name), encoding="utf-8", errors="replace") as f:
                files += f.read()
        with open(post_queue.POSTED, encoding="utf-8") as f:
            files += f.read()
        self.assert_no_secrets(out + out2 + out3 + files)

    def test_unknown_is_not_resent_and_4xx_is_retried(self):
        self.write_queue([{"id": "x1", "sns": "x", "scheduled_at": "2026-11-01T08:00:00+09:00",
                           "qc": "ok", "text": "本文"}])
        self.mock.fail_with = 500
        code, out = self.run_queue()
        self.assertEqual(code, 1)
        self.assertEqual(self.state()["x1"]["status"], "unknown")
        self.assertIn("***", out)
        self.assert_no_secrets(out)
        self.mock.fail_with = None
        code, out = self.run_queue()
        self.assertEqual(len(self.mock.requests), 1, out)  # 出し直さない
        # 人が確認して行を消す → 出し直す
        os.remove(os.path.join(self.qdir, "queue_state.json"))
        self.mock.fail_with = 403
        code, out = self.run_queue()
        self.assertNotIn("x1", self.state())               # 4xx は確実に出ていない → 記録を消す
        self.mock.fail_with = None
        code, out = self.run_queue()
        self.assertEqual(self.state()["x1"]["status"], "posted")

    def test_missing_env_skips_x(self):
        for k in FAKE:
            os.environ.pop(k, None)
        self.write_queue([{"id": "x1", "sns": "x", "scheduled_at": "2026-11-01T08:00:00+09:00",
                           "qc": "ok", "text": "本文"}])
        code, out = self.run_queue()
        self.assertEqual(code, 3, out)
        self.assertEqual(self.mock.requests, [])

    def test_too_long_stops_queue(self):
        self.write_queue([{"id": "x1", "sns": "x", "scheduled_at": "2026-11-01T08:00:00+09:00",
                           "qc": "ok", "text": "あ" * 141}])
        code, out = self.run_queue()
        self.assertEqual(code, 1)
        self.assertIn("X の上限 280", out)
        self.assertEqual(self.mock.requests, [])


if __name__ == "__main__":
    c._SECRETS.clear()
    unittest.main(verbosity=2)

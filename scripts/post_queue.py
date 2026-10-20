#!/usr/bin/env python3
"""投稿キュー（output/YYYY-MM-DD/queue.json）から、時刻が来た投稿だけを投稿する。

- data/config.md の AUTO_POST が true のときだけ送信する（false なら何も送らずに終わる）。
- qc が "ok"（品質管理を通った）の投稿だけを扱う。
- 投稿したら data/posted.md に追記し、二重投稿を防ぐため
  output/YYYY-MM-DD/queue_state.json に「投稿済みID」を記録する（秘密の値は書かない）。
- 送信の直前に queue_state.json へ「送信中」と書き、成功したら「投稿済み」に書きかえる。
  途中で落ちた・タイムアウトした等で「投稿されたか不明」になったものは、自動では出し直さない
  （SNSで確認して、人が queue_state.json のその行を消す）。
- 同時に2つ動かないように、output/日付/queue.lock でロックする（cron の重なり対策）。
- --dry-run：送信も記録もせず、投稿される予定の内容を表示する（環境変数も不要）。
- X は料金対策として、URL を含む投稿はスキップして警告する。1日の本数は data/config.md の
  X_DAILY_LIMIT（既定 5）まで。

使い方:
  python3 scripts/post_queue.py                      # 今日（JST）のキュー
  python3 scripts/post_queue.py --date 2026-11-01
  python3 scripts/post_queue.py --dry-run --now 2026-11-01T13:00:00+09:00
キューの形式は scripts/README.md を参照。
"""

import argparse
import contextlib
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sns_common as c  # noqa: E402
import post_threads  # noqa: E402
import post_bluesky  # noqa: E402
import post_x  # noqa: E402

ROOT = os.path.dirname(HERE)
CONFIG = os.path.join(ROOT, "data", "config.md")
POSTED = os.path.join(ROOT, "data", "posted.md")
SNS_LABEL = {"threads": "Threads", "bluesky": "Bluesky", "x": "X"}
SNS_ENV = {"threads": ["THREADS_ACCESS_TOKEN", "THREADS_USER_ID"],
           "bluesky": ["BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD"],
           "x": list(post_x.ENV_NAMES)}
SNS_MODULE = {"threads": post_threads, "bluesky": post_bluesky, "x": post_x}
DEFAULT_X_DAILY_LIMIT = 5


# ---- 設定 ---------------------------------------------------------------

def read_config(path=None):
    path = path or CONFIG
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        c.fail("設定ファイルがありません: {}".format(path))
    m = re.search(r"^AUTO_POST:\s*(\S+)", text, re.M)
    if not m:
        c.fail("data/config.md に AUTO_POST: の行がありません")
    val = m.group(1).strip().lower()
    if val not in ("true", "false"):
        c.fail("AUTO_POST は true か false にしてください（今: {}）".format(val))
    tzm = re.search(r"^TIMEZONE:\s*(\S+)", text, re.M)
    xm = re.search(r"^X_DAILY_LIMIT:\s*(\S+)", text, re.M)
    x_limit = DEFAULT_X_DAILY_LIMIT
    if xm:
        if not xm.group(1).isdigit():
            c.fail("X_DAILY_LIMIT は 0 以上の整数にしてください（今: {}）".format(xm.group(1)))
        x_limit = int(xm.group(1))
    return {"auto_post": val == "true", "timezone": tzm.group(1) if tzm else "Asia/Tokyo",
            "x_daily_limit": x_limit}


def get_tz(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        if name == "Asia/Tokyo":
            return datetime.timezone(datetime.timedelta(hours=9), "JST")
        c.fail("タイムゾーン {} を読めません".format(name))


# ---- キュー -------------------------------------------------------------

def parse_time(s, tz):
    try:
        if isinstance(s, str) and s.endswith("Z"):
            s = s[:-1] + "+00:00"  # Python 3.10 以前の fromisoformat は "Z" を読めない
        dt = datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        raise ValueError("scheduled_at の形式が不正です: {!r}（例: 2026-11-01T08:00:00+09:00）".format(s))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt.astimezone(tz)  # 表示も比較もJSTにそろえる


def load_queue(path, tz):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        c.fail("キューがありません: {}".format(path))
    except ValueError as e:
        c.fail("queue.json が JSON として読めません: {}".format(e))
    posts = data.get("posts")
    if not isinstance(posts, list):
        c.fail("queue.json に \"posts\" の配列がありません")
    errors, seen = [], set()
    for i, p in enumerate(posts):
        where = "posts[{}]".format(i)
        for key in ("id", "sns", "scheduled_at", "text"):
            if not p.get(key):
                errors.append("{}: {} がありません".format(where, key))
        if p.get("id") in seen:
            errors.append("{}: id {} が重複しています".format(where, p.get("id")))
        seen.add(p.get("id"))
        if p.get("sns") not in SNS_LABEL:
            errors.append("{}: sns は threads / bluesky / x のどれかにしてください（今: {}）".format(
                where, p.get("sns")))
            continue
        try:
            p["_dt"] = parse_time(p.get("scheduled_at"), tz)
        except ValueError as e:
            errors.append("{}: {}".format(where, e))
        if p.get("text"):
            try:
                SNS_MODULE[p["sns"]].check_text(p["text"])  # X の URL はここでは止めず、投稿時にスキップ
            except ValueError as e:
                errors.append("{} ({}): {}".format(where, p.get("id"), e))
    for p in posts:
        r = p.get("reply_to")
        if r and r not in seen:
            errors.append("{}: reply_to の {} がキューにありません".format(p.get("id"), r))
        elif r:
            parent = next(q for q in posts if q.get("id") == r)
            if r == p.get("id"):
                errors.append("{}: reply_to が自分自身です".format(p.get("id")))
            elif parent.get("sns") != p.get("sns"):
                errors.append("{}: reply_to の {} は別のSNSの投稿です（返信は同じSNSどうしだけ）".format(
                    p.get("id"), r))
    if errors:
        c.fail("queue.json に問題があります:\n  " + "\n  ".join(errors))
    return posts


def load_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"posted": {}}


def x_url_count(p):
    return len(post_x.find_urls(p["text"])) if p["sns"] == "x" else 0


def x_used_today(done):
    """この日のキューで、X に出した（出したかもしれない）本数。sending / unknown も数える。"""
    return sum(1 for r in done.values() if r and r.get("sns") == "x")


def is_posted(rec):
    """queue_state.json の1件が「投稿済み」か（古い形式は status が無い＝投稿済み）。"""
    return bool(rec) and rec.get("status", "posted") == "posted"


@contextlib.contextmanager
def run_lock(path):
    """同じ日のキューを2つのプロセスが同時に処理しないようにする（二重投稿の防止）。"""
    try:
        import fcntl
    except ImportError:  # Windows など。ロックなしで動かす
        yield
        return
    with open(path, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            c.fail("別の post_queue.py が実行中です（{}）。終わってからもう一度実行してください".format(
                os.path.basename(path)))
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def append_posted(date_str, sns, neta, text):
    head = re.sub(r"\s+", " ", text).strip()[:30].replace("|", "｜")
    neta = (neta or "").replace("|", "｜").replace("\n", " ")
    with open(POSTED, "a", encoding="utf-8") as f:
        f.write("| {} | {} | {} | {} |\n".format(date_str, SNS_LABEL[sns], neta, head))


# ---- メイン -------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="投稿キューから、時刻が来た投稿を投稿する")
    ap.add_argument("--date", help="キューの日付 YYYY-MM-DD（既定：今日のJST）")
    ap.add_argument("--queue", help="queue.json のパス（既定：output/日付/queue.json）")
    ap.add_argument("--dry-run", action="store_true", help="送信も記録もせず、内容を表示する")
    ap.add_argument("--now", help="現在時刻の上書き（動作確認用。例 2026-11-01T13:00:00+09:00）")
    ap.add_argument("--max-delay-hours", type=float, default=6.0,
                    help="予定時刻からこの時間より遅れた投稿は出さない（既定 6）")
    ap.add_argument("--threads-wait", type=int, default=post_threads.DEFAULT_WAIT_SEC,
                    help="Threads のコンテナ作成から公開までの待ち秒数（既定 30）")
    args = ap.parse_args(argv)

    cfg = read_config()
    tz = get_tz(cfg["timezone"])
    now = (parse_time(args.now, tz) if args.now else datetime.datetime.now(tz)).astimezone(tz)  # JSTで扱う
    date_str = args.date or now.astimezone(tz).strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        c.fail("--date は YYYY-MM-DD で指定してください")
    qpath = args.queue or os.path.join(ROOT, "output", date_str, "queue.json")
    spath = os.path.join(os.path.dirname(os.path.abspath(qpath)), "queue_state.json")

    posts = load_queue(qpath, tz)
    if args.dry_run or not cfg["auto_post"]:
        return run(args, cfg, tz, now, date_str, qpath, spath, posts)
    with run_lock(os.path.join(os.path.dirname(os.path.abspath(qpath)), "queue.lock")):
        return run(args, cfg, tz, now, date_str, qpath, spath, posts)


def run(args, cfg, tz, now, date_str, qpath, spath, posts):
    state = load_state(spath)
    done = state.setdefault("posted", {})

    print("キュー: {}（{}件）".format(os.path.relpath(qpath, ROOT), len(posts)))
    print("現在時刻: {}  AUTO_POST: {}".format(now.isoformat(timespec="minutes"),
                                             "true" if cfg["auto_post"] else "false"))
    if not cfg["auto_post"] and not args.dry_run:
        print("AUTO_POST が false なので投稿しません（output/日付/queue.md を人が見て投稿する運用です）。")
        return 0

    max_delay = datetime.timedelta(hours=args.max_delay_hours)
    due, notes = [], []
    x_left = max(0, cfg["x_daily_limit"] - x_used_today(done))
    for p in sorted(posts, key=lambda x: x["_dt"]):
        pid = p["id"]
        if pid in done:
            if not is_posted(done[pid]):
                notes.append("  - {}: 前回、投稿できたか分からないまま終わっています（{}）。SNSで確認し、"
                             "出ていなければ queue_state.json からこの id を消してください".format(
                                 pid, done[pid].get("status")))
            continue
        if str(p.get("qc", "")).lower() != "ok":
            notes.append("  - {}: 品質管理が未通過（qc != ok）なので出しません".format(pid))
            continue
        if p["_dt"] > now:
            notes.append("  - {}: まだ時刻前（{}）".format(pid, p["_dt"].strftime("%H:%M")))
            continue
        if now - p["_dt"] > max_delay:
            notes.append("  - {}: 予定より {} 時間以上遅れたので出しません（手で判断してください）".format(
                pid, args.max_delay_hours))
            continue
        if p["sns"] == "x":
            if x_url_count(p):
                print("警告: {}: X の投稿に URL が入っているのでスキップします（URL つきは料金が高い。"
                      "URL はプロフィールや返信に置いてください）".format(pid), file=sys.stderr)
                notes.append("  - {}: URL を含む X 投稿なのでスキップ（料金対策）".format(pid))
                continue
            if x_left <= 0:
                notes.append("  - {}: X の1日の上限 {} 本に達したので出しません（X_DAILY_LIMIT）".format(
                    pid, cfg["x_daily_limit"]))
                continue
            x_left -= 1
        due.append(p)

    if notes:
        print("今回は出さないもの:")
        print("\n".join(notes))

    if args.dry_run:
        print("[dry-run] 送信しません。記録もしません。")
        if not cfg["auto_post"]:
            print("  ※ AUTO_POST が false なので、本番で実行しても送信されません。")
        for sns, names in SNS_ENV.items():
            ok = all(os.environ.get(n) for n in names)
            print("  {} の環境変数: {}".format(SNS_LABEL[sns], "設定あり" if ok else "未設定（本番ではこのSNSは飛ばします）"))
        print("時刻が来た投稿: {}件".format(len(due)))
        for p in due:
            n = SNS_MODULE[p["sns"]].check_text(p["text"])[0]
            unit = "（Xの数え方）" if p["sns"] == "x" else "字"
            print("\n=== {} | {} | {} | {}{} ===".format(p["id"], SNS_LABEL[p["sns"]],
                                                     p["_dt"].strftime("%Y-%m-%d %H:%M"), n, unit))
            if p.get("reply_to"):
                print("（{} への返信として投稿）".format(p["reply_to"]))
            print(p["text"])
        return 0

    if not due:
        print("時刻が来た未投稿の投稿はありません。")
        return 0

    # SNSごとにログイン情報を1回だけ用意する。環境変数が無いSNSは飛ばす（キューには残る）。
    creds, unavailable = {}, {}
    exit_code = 0
    for p in due:
        sns, pid = p["sns"], p["id"]
        if sns in unavailable:
            print("  - {}: {} は使えないので飛ばしました".format(pid, SNS_LABEL[sns]))
            continue
        reply_info = None
        if p.get("reply_to"):
            parent = done.get(p["reply_to"])
            if not is_posted(parent) or parent.get("sns") != sns:
                print("  - {}: 返信先 {} がまだ投稿されていないので待ちます".format(pid, p["reply_to"]))
                continue
            reply_info = parent
        try:
            if sns not in creds:
                creds[sns] = {"threads": post_threads.load_credentials, "bluesky": post_bluesky.login,
                              "x": post_x.load_credentials}[sns]()
            if sns == "x" and x_used_today(done) >= cfg["x_daily_limit"]:  # 念のため送る直前にも確認
                print("  - {}: X の1日の上限 {} 本に達したので出しません".format(pid, cfg["x_daily_limit"]))
                continue
            # 送る直前に「送信中」を記録。ここで落ちても、次の実行で自動の出し直しはしない
            done[pid] = {"sns": sns, "status": "sending",
                         "started_at": datetime.datetime.now(tz).isoformat(timespec="seconds")}
            save_state(spath, state)
            if sns == "threads":
                rid = reply_info["post_id"] if reply_info else None
                post_id = post_threads.post(p["text"], reply_to_id=rid, wait_sec=args.threads_wait,
                                            creds=creds[sns])
                rec = {"sns": sns, "post_id": post_id}
            elif sns == "x":
                rid = reply_info["post_id"] if reply_info else None
                post_id = post_x.post(p["text"], reply_to_id=rid, creds=creds[sns], allow_url=False)
                rec = {"sns": sns, "post_id": post_id}
            else:
                reply = None
                if reply_info:
                    root = reply_info.get("root") or {"uri": reply_info["uri"], "cid": reply_info["cid"]}
                    reply = {"root": root, "parent": {"uri": reply_info["uri"], "cid": reply_info["cid"]}}
                res = post_bluesky.post(p["text"], session=creds[sns], reply=reply)
                rec = {"sns": sns, "uri": res["uri"], "cid": res["cid"]}
                if reply:
                    rec["root"] = reply["root"]
        except c.MissingEnvError as e:
            unavailable[sns] = True
            print("警告: {}".format(c.redact(e)), file=sys.stderr)
            print("  - {}: {} の環境変数が無いので飛ばしました（キューには残ります）".format(pid, SNS_LABEL[sns]))
            exit_code = max(exit_code, 3)
            continue
        except c.PostError as e:
            print("エラー: {} の投稿に失敗: {}".format(pid, c.redact(e)), file=sys.stderr)
            if done.get(pid, {}).get("status") == "sending":
                if getattr(e, "maybe_posted", False):
                    done[pid]["status"] = "unknown"
                    print("  - {}: 投稿されたか分かりません。二重投稿を防ぐため、自動では出し直しません"
                          "（SNSで確認してください）".format(pid), file=sys.stderr)
                else:
                    del done[pid]  # 確実に出ていない → 次の実行で出し直す
                save_state(spath, state)
            if sns not in creds:
                unavailable[sns] = True  # ログイン失敗。同じSNSは今回あきらめる
            exit_code = 1
            continue
        rec["status"] = "posted"
        rec["posted_at"] = datetime.datetime.now(tz).isoformat(timespec="seconds")
        done[pid] = rec
        save_state(spath, state)
        append_posted(date_str, sns, p.get("neta", ""), p["text"])
        print("  + {}: {} に投稿しました".format(pid, SNS_LABEL[sns]))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

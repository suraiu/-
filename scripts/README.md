# 投稿スクリプト（Threads / Bluesky）

Python 3 の標準ライブラリだけで動く（外部ライブラリなし。Python 3.9 以上、3.13 で確認）。

| ファイル | 役割 |
|---|---|
| `post_threads.py` | Threads にテキストを1本投稿（コンテナ作成 → 公開の2段階） |
| `post_bluesky.py` | Bluesky にテキストを1本投稿（createSession → createRecord） |
| `post_queue.py` | `output/YYYY-MM-DD/queue.json` から、時刻が来た投稿だけを投稿して記録 |
| `sns_common.py` | 共通部品（環境変数チェック、HTTP、秘密の伏せ字、文字数の数え方） |
| `queue.example.json` | キューの見本 |

## 1. 準備（オーナーが1回だけ）

トークン・パスワードは **環境の設定（シークレット）に登録する**。ファイル・チャット・日報には貼らない。

| SNS | 環境変数 | 中身 |
|---|---|---|
| Threads | `THREADS_ACCESS_TOKEN` | `threads_content_publish` 権限つきのユーザーアクセストークン |
| Threads | `THREADS_USER_ID` | Threads のユーザーID（数字） |
| Bluesky | `BLUESKY_HANDLE` | ハンドル（例 `xxxx.bsky.social`） |
| Bluesky | `BLUESKY_APP_PASSWORD` | 設定 → アプリパスワードで作ったもの（ふだんのパスワードは使わない） |

任意：`THREADS_API_BASE`（既定 `https://graph.threads.net/v1.0`）、`BLUESKY_PDS`（既定 `https://bsky.social`）。

## 2. 使い方

```bash
# 1本だけ投稿（--dry-run なら送信しない。環境変数も要らない）
python3 scripts/post_threads.py --dry-run "本文"
python3 scripts/post_threads.py --file post.txt
python3 scripts/post_bluesky.py --dry-run "本文"

# キューから投稿（cron などで15分おきに回す想定）
python3 scripts/post_queue.py                       # 今日（JST）の output/日付/queue.json
python3 scripts/post_queue.py --date 2026-11-01
python3 scripts/post_queue.py --dry-run --now 2026-11-01T13:00:00+09:00   # 動作確認
```

`post_queue.py` のオプション：

| オプション | 意味 |
|---|---|
| `--date YYYY-MM-DD` | どの日のキューを読むか（既定：今日のJST） |
| `--queue PATH` | queue.json の場所を直接指定 |
| `--dry-run` | 送信も記録もしない。時刻が来た投稿の本文・文字数・環境変数の有無（あり/なしだけ）を表示 |
| `--now ISO8601` | 現在時刻の上書き（動作確認用） |
| `--max-delay-hours N` | 予定時刻から N 時間より遅れた投稿は出さない（既定 6。止まっていた後に一気に出さないため） |
| `--threads-wait N` | Threads のコンテナ作成から公開までの待ち秒数（既定 30） |

## 3. post_queue.py の動き

1. `data/config.md` の `AUTO_POST` を読む。**`false` なら何も送らずに終わる**（`--dry-run` は表示だけする）。
2. `queue.json` を検査する（必須項目、SNS名、時刻の形式、id の重複、文字数）。問題があれば1件も出さずに止まる。
3. `qc` が `"ok"` で、`scheduled_at` が現在時刻以前で、まだ投稿していないものだけを、時刻順に投稿する。
   時刻はすべて日本時間（`TIMEZONE`）にそろえて比べる。`--now` に `Z`（UTC）を付けてもJSTに直して扱う。
   同じ日のキューを2つのプロセスが同時に処理しないよう、`output/日付/queue.lock` でロックする（cron の重なり対策）。
4. 環境変数が無いSNSは、そのSNSの投稿だけ飛ばす（キューには残る。終了コード 3）。
5. 1本投稿するごとに：
   - 送る直前に `output/YYYY-MM-DD/queue_state.json` へ `"status": "sending"` を書き、成功したら投稿済みID（SNS側の投稿ID／URI）と `"status": "posted"` に書きかえる → 次に回したときの二重投稿を防ぐ
   - タイムアウト・接続切れ・5xx など「投稿されたか分からない」失敗や、途中で落ちた場合は `"unknown"`／`"sending"` のまま残し、**自動では出し直さない**。
     SNSの画面で確認し、出ていなければ `queue_state.json` からその id の行を消すと、次の実行で出し直す。
     4xx など確実に出ていない失敗は記録を消して、次の実行で出し直す。
   - `data/posted.md` に `| 日付 | SNS | ネタ | 本文の冒頭30字 |` を追記する
6. `reply_to` がある投稿（クイズの答え合わせなど）は、返信先が投稿済み（`posted`）になってから、その返信として投稿する。返信先は同じSNSの投稿に限る（違えばキュー検査で止める）。

終了コード：`0` 正常／`1` 投稿の失敗やキューの不備／`2` 単体スクリプトで環境変数が無い／`3` キュー実行で環境変数が無いSNSを飛ばした。

## 4. queue.json の形式

```json
{
  "date": "2026-11-01",
  "posts": [
    {
      "id": "d01-t1",
      "sns": "threads",
      "scheduled_at": "2026-11-01T08:00:00+09:00",
      "neta": "C型 謝罪メールのテンプレ",
      "qc": "ok",
      "text": "本文"
    },
    {
      "id": "d01-t2-ans",
      "sns": "threads",
      "scheduled_at": "2026-11-01T20:30:00+09:00",
      "neta": "A型 答え合わせ",
      "qc": "ok",
      "reply_to": "d01-t2",
      "text": "答え合わせの本文"
    }
  ]
}
```

| 項目 | 必須 | 説明 |
|---|---|---|
| `id` | ○ | キューの中で一意。おすすめ：`d日付-SNS頭文字番号`（`d01-t1`, `d01-b1`） |
| `sns` | ○ | `threads` または `bluesky` |
| `scheduled_at` | ○ | ISO 8601。タイムゾーンを書かなければ `data/config.md` の `TIMEZONE`（Asia/Tokyo） |
| `text` | ○ | 本文。Threads 500字、Bluesky 300字（書記素）・3,000バイトまで。超えたらキュー全体を止める |
| `qc` | ○ | 品質管理を通ったら `"ok"`。それ以外は投稿しない |
| `neta` | – | `data/posted.md` の「ネタ」欄に入る |
| `reply_to` | – | 同じキューの、同じSNSの投稿の `id`。その投稿への返信になる |

見本：`scripts/queue.example.json`。`output/YYYY-MM-DD/queue.md`（人が見る用）と並べて置く。

## 5. 秘密の扱い

- トークン・パスワード・Bluesky の accessJwt はメモリにだけ持ち、**画面・ログ・ファイルに出さない**。
  API のエラー本文に値が混ざっていても `***` に置き換えてから表示する（`sns_common.redact`）。
- 秘密は URL に入れない（Threads の `access_token` は POST の本文で送る）。
- `queue_state.json` に入るのは投稿ID・URI・CID・時刻だけ。
- `--dry-run` は環境変数の「あり／なし」だけを表示する。

## 6. 要確認（API仕様は WebSearch の抜粋で確認。公式ページ本文は開けていない）

**Threads**
- ホスト：抜粋の例は `graph.threads.net/v1.0`。`graph.threads.com` と書いた版もある → 使えなければ `THREADS_API_BASE` で差し替える。
- `access_token` を POST 本文で送る方式で通るか（`Authorization: Bearer` ヘッダーでも通るかは未確認）。
- 文字数：500字。絵文字は UTF-8 のバイト数で数えるという抜粋があるので、絵文字をバイト換算した長さでも500以内を確認している（絵文字の判定は近似）。
- 返信の `reply_to_id`：抜粋レベルの情報で実装。
- 作成から公開までの待ち時間：約30秒を勧めているとされる。テキストだけなら短くてもよいかは未確認。
- 投稿上限：24時間で250件（公式の抜粋）。1時間50件という業者の記述もあるが未確認。

**Bluesky**
- 書記素の数え方：標準ライブラリに書記素分割が無いので近似（日本語・英数字は正確、複雑な絵文字は誤差の可能性）。
- `langs: ["ja"]` を付けている（任意項目とされる）。
- URL・ハッシュタグは facets が無いとリンクにならない（本文にリンクを入れない方針なので未実装）。
- createSession を何度も呼ぶとレート制限にかかるという抜粋あり → 1回の実行で1回だけログインする。

**どちらも**：実際の API にはまだ送っていない（トークンが無いため）。最初の本番は、オーナーの立ち会いで
`post_threads.py` / `post_bluesky.py` を1本ずつ試してから `AUTO_POST: true` にする。

## 7. ローカルで確認したこと（2026-10-20）

品質管理AIの再確認（2026-10-20 夜）：`py_compile`、3本の `--dry-run`、モックサーバーでの
「二重投稿しない／公開段階の500や接続切れで unknown になり出し直さない／人が消すと出し直す／返信／
ロック中は止まる／出力とファイルに秘密が出ない」を確認。

- `--dry-run`（3本とも）、文字数オーバーで止まること（Threads 501字、Bluesky 301字）。
- 環境変数が無いときのエラー（単体：終了コード2／キュー：そのSNSだけ飛ばして終了コード3）。
- `AUTO_POST: false` のとき送信しないこと。
- ローカルのモックサーバー（127.0.0.1）を相手にした AUTO_POST=true の一連の流れ：
  時刻前は出さない・二重投稿しない・返信（reply_to）・遅れすぎた投稿は出さない・`data/posted.md` への追記・
  エラー本文に混ざったパスワードが `***` になること・書き出したファイルに秘密が入らないこと。

参考（抜粋で確認）：[Threads Posts（Meta）](https://developers.facebook.com/docs/threads/posts/)、[Threads Troubleshooting（Meta）](https://developers.facebook.com/docs/threads/troubleshooting)、[Bluesky: create post](https://docs.bsky.app/blog/create-post)、[Bluesky: Get Started](https://docs.bsky.app/docs/get-started)、[Bluesky limits（OpenTweet）](https://opentweet.io/answers/bluesky-limits)

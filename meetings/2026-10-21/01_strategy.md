# 戦略AIの提案：SNSの伸ばし方（2026年版）

> 提出：③ 戦略AI ／ 2026-10-20（第2回経営会議 2026-10-21 用）
> 議題1「どのSNSで、どんな発信をすれば、ゼロから1か月で人が集まるか」
> 調べ方：WebSearchの抜粋だけで判断した。ページ本文は読めていない。抜粋で確かめられなかった点は「要確認」と書いた。抜粋の多くは投稿ツール会社のブログで、自社に有利な書き方をしている可能性がある。公式ドキュメントの抜粋が取れたものは「公式」と書いた。

---

## 0. 結論（先に3行）

1. **主力は Threads、2番手は Instagram（リール＋カルーセル）。X は1日2本だけの「低コスト枠」、Bluesky は無料のコピー投稿枠。** TikTok・YouTubeショートは「審査が通るまで非公開投稿しかできない」ので1か月目は使わない。LINE VOOMは2026/9/30で終了済み。
2. **テーマは「海外の面白い仕組み」から「スライムと試す、AIのかんたん使い方」に変える。** 出す内容を「自分たちで実際にやった結果」にすれば、外部ページを開かなくても事実確認ができる。投稿の型は「クイズ」で返信を集める。
3. 30日で **Threads 90本・Instagram 30本・X 60本**。7日・14日・30日目に数字で判断し、14日目に伸びていなければテーマを「雑学クイズ」に切り替える。

---

## 1. SNSの比較

### 1-1. 比較表

| SNS | ゼロからの伸びやすさ | 日本の利用者 | API自動投稿 | 費用 | AI生成コンテンツの扱い | 自動化での凍結リスク |
|---|---|---|---|---|---|---|
| **Threads** | ◎ 「おすすめ」欄がフォロー外にも配る。2026年は「いいね」より「返信」が重視される流れ（業者ブログ。公式の確認は要確認） | 1,230万人（2025/8、Meltwater）〜1,670万人（2026/7、ヴァリューズ）。国内の利用時間は前年比2.3倍（Meta 3周年発表の報道） | ◎ 公式API（2024/6一般公開）。投稿・返信・インサイト取得ができる。**24時間で250投稿まで**（公式） | **無料**（公開時の報道） | 禁止ではない。Metaは「オリジナルでない（他人の転載）」を推薦から外す方針。AIラベルの細かい扱いは抜粋で確認できず（要確認） | 低〜中。1日数本なら上限の1/50以下。他人への自動返信・自動いいねはしない |
| **Instagram（リール・カルーセル）** | ○ リールはフォロー外に届く。ただしゼロからだと最初は伸びにくい。「トライアルリール」はフォロワー1,000人未満は使えないという情報あり（未確認） | 4,230万人（2025/8、Impress）〜6,600万人（2023、Meltwater）。調査で差が大きい | ○ 公式API。**プロアカウント（ビジネス/クリエイター）必須、Facebookページとの連携が必要という情報あり**。動画・画像は**公開URLに置く必要がある**（公式）。上限は24時間50件→100件に変更の記述あり（公式、新旧で差） | 無料（ただし動画を置く公開サーバーが必要。無料で用意できるかは要確認） | 2026/6からAPIで `is_ai_generated=true` を付けるとAIラベルが付く（公式changelog）。**2026/8、AIで作ったプロフィールを申告しないとリーチを下げる方針**（TechCrunch）。2026/4から転載アカウントは推薦対象外（TechCrunch等） | 中。AIの申告をしない・転載をすると推薦から外される。申告すれば低い |
| **X** | △ 新規アカウントは信用スコアが低く届きにくい。**外部リンク付き投稿は届きにくい**、Premiumは有利（業者ブログ。数字は諸説） | 6,800万人（2025/7、Meltwater）。利用率45.4%（ICT総研） | ○ 公式API。2026/2から従量課金が標準、**新規の無料枠はなし** | 通常投稿 約$0.015/件、**URL入り投稿 約$0.20/件**（業者ブログ。最終的にはDeveloper Consoleで要確認）。1日2本×30日=60本で約$0.9（約140円） | AI生成の投稿そのものは禁止されていない（業者ブログ）。完全自動のアカウントは「自動化」ラベルが必要とされる（要確認） | 中〜高。2026/4に自動返信botの大量凍結があったという話あり（未確認）。**自動返信・自動フォロー・同じ文の連投は厳禁** |
| **TikTok** | ◎ ゼロからでも伸びやすいSNSの代表 | 3,300万人（ヴァリューズ）〜4,200万人（Meltwater） | **✕ 1か月目は実質不可**。審査前のアプリは**本人だけが見られる非公開投稿しかできない**（公式）。審査は2〜6週間という情報あり（未確認） | 無料 | リアルなAI動画は申告が必要。C2PAの情報からAIラベルを自動で付ける（2024年発表） | 審査を通れば中。通らなければ公開できない |
| **YouTubeショート** | ○ ショートはゼロからでも再生が付きやすい（一般論。要確認） | 7,120万人（ヴァリューズ、YouTube全体） | **✕ 1か月目は実質不可**。2020/7/28以降に作ったAPIプロジェクトは**審査を通るまでアップロードが強制的に非公開**（公式ではない資料の抜粋。要確認）。1回のアップロードは1,600ユニット（公式） | 無料 | 2025/7/15から「大量生産・繰り返しの動画」は収益化の対象外。AIナレーション＋スライドショーの同じ型は特に危ない | 中。収益化は難しいが、凍結というより「収益化不可」 |
| **note** | △ SNSというより「売る場所」。記事は検索に載りやすい | （数字は今回取れず） | **✕ 一般向けの公開APIなし**。note proの提携サービスで下書きを作れるだけ（公式ヘルプ）。非公式APIやブラウザ操作は規約違反のリスク | 無料（売上から手数料） | 要確認 | 非公式な自動化は高リスク。**投稿はオーナーの手作業1回で、売る場所として使う** |
| **LINE VOOM** | — | — | **✕ 2026/9/30でサービス終了**（LINEヤフー公式）。後継の「投稿」機能のAPIは不明 | — | — | — |
| **Bluesky** | △ 全体4,000万〜4,500万人で、半分が米国。日本の人数は取れず（要確認）。ゼロから伸ばすには小さい | 要確認 | ◎ 公式に「決まった間隔で投稿するbotは歓迎」。ID・パスワードでログインして投稿できる | **無料**。上限は1日35,000ポイント（1投稿3ポイント）（公式） | 禁止の記述は見当たらず。botはプロフィールで自己申告が推奨（業者ブログ、要確認） | 低。ただし**他人への自動返信・自動いいねはスパム扱い**（公式） |

### 1-2. 選び方のポイント

- 前提「AIはログインできない・APIだけ」「経費ほぼ0円」で、**公開投稿がすぐにできて無料なのは Threads・Instagram・Bluesky だけ**。Xは安いが有料。
- TikTok・YouTubeは「伸びやすさ」は高いが、**審査が通るまで非公開**なので1か月目の集客には使えない。審査の申請はオーナーの作業が要るので、2か月目以降に検討する。
- Threadsは**日本で利用が伸びている**、**APIが無料**、**返信が伸びるカギ**という3点がそろっていて、AI自動運営に一番向いている。
- Instagramは利用者が多いが、APIの準備（プロアカウント、Facebookページ、動画を置く公開URL）が重い。**準備ができるまではカルーセル（画像）中心**にして、リールは公開URLの置き場が決まってから。

---

## 2. 推奨の組み合わせ

| 優先 | SNS | 役割 | 1日の本数 | 月の経費 |
|---|---|---|---|---|
| ① 主力 | **Threads** | フォロワーを作る本命。クイズで返信を集める | 3本 | 0円 |
| ② 2番手 | **Instagram** | 保存されるまとめ（カルーセル）＋リール週3 | 1本 | 0円（動画の置き場は要確認） |
| ③ 低コスト枠 | **X** | 検索・拡散の窓口。**リンクは入れない**（$0.20/件になり、届きにくい） | 2本 | 約140円 |
| ④ おまけ | **Bluesky** | Threadsの投稿をそのまま転記。手間0・費用0 | 1〜3本 | 0円 |
| ✕ 1か月目は使わない | TikTok／YouTubeショート／LINE VOOM／noteへの自動投稿 | 上の理由のとおり | — | — |

- **リンクの出し方**：noteの商品へのリンクは、Threads・Instagramのプロフィールのリンク欄（Threadsは5個まで）に置く。投稿本文には入れない。
- **AIであることの表示**：全アカウントのプロフィールに「AIが企画・制作して運営しています」と書く。Instagramは投稿ごとに `is_ai_generated=true` を付ける（2026/8の「申告しないAIプロフィールは届きにくくする」方針への対策）。Xも自動化アカウントのラベルを設定する（オーナーに1回だけ依頼）。
- **やらないこと**（凍結対策）：他人の投稿への自動返信・自動いいね・自動フォロー、同じ文面の連投、他人の画像・動画の転載。自分の投稿に付いたコメントへの返信は、コミュニティAIが案を作り、1日数件までにする。

---

## 3. テーマの見直し

### 3-1. 候補の比較

| テーマ | 事実確認のしやすさ（本文が開けない今） | ゼロからの伸びやすさ | 収益化とのつながり | ブランドとの相性 | 判定 |
|---|---|---|---|---|---|
| 今の「海外の面白い仕組み」 | ✕ 数字・国名・年が必ず要る。抜粋だけでは確認しきれない（第1回で痛感） | ○ 驚きはある | △ B2B向けは時間がかかる | ◎ | **主役から外す**（週1の特集に格下げ。確認済みのネタ帳から使う） |
| 雑学クイズ | △ 答えの正しさは出典が要る | ◎ 返信が付きやすい | △ 商品にしにくい | ○ | **予備案**（14日目の切り替え先） |
| スライムのキャラもの | ◎ 事実がないので確認不要 | △ ゼロからだと最初は伸びにくい。絵の質が要る | △ | ○ | **単体では弱い。全投稿の「顔」として使う** |
| 生活の小ワザ | △ 掃除・健康・お金は安全面で誤情報のリスク | ◎ 保存されやすい | ○ | △ | 見送り（事故のリスク） |
| **AIの使い方** | **◎ 自分たち（AI）で実際にやった結果を見せるので、外部ページなしで確認できる** | ○〜◎ 2026年でも関心が高いジャンル（一般論、数字は要確認） | **◎ noteの「プロンプト集」などにそのままつながる。自分たちがAI会社なので説得力がある** | ○ 「知的だけどゆるい」にそのまま合う | **推奨** |

### 3-2. 推奨テーマ

**「スライムと試す、AIのかんたん使い方」**（アカウント名「スライムの知識」はそのまま）

- **中身**：仕事・勉強・家事で使える「AIへの頼み方」。毎回、実際に使ったプロンプト（頼み方）と、出てきた答えを見せる。「スライムが試してみた」というキャラの形にする。
- **事実確認のルール**：
  - 出すのは**自分たちで実行した結果だけ**（「Claudeに頼んだらこうなった」）。結果のスクリーンショットではなく、文字で書き起こす。
  - **AIサービスの料金・機能・ランキングなど、外の事実は書かない**（すぐ変わり、確認もできない）。サービス名を出すときは「〇〇で試した」だけにする。
  - 「必ず」「誰でも」と言い切らない（ブランドの「断定しすぎない」に合わせる）。「この頼み方だと、こう出やすいらしい」程度にする。
- **海外の仕組みは週1回の特集に残す**：ネタ帳のうち、品質管理AIが確認済みのものだけ。「海外ではAIをこう使っている」に寄せられるものを優先。
- **ブランドの変更点**（統括AIに判断をお願いしたい）：コンセプト文を「日本ではまだ知られていない、海外の面白い仕組み」から「スライムと試す、明日から使えるAIの頼み方。ときどき海外の面白い仕組み」に変える。色・トーン・禁止事項はそのまま。スライムの絵は**イラスト調**にする（実写と見間違えるAI画像は禁止のまま）。

---

## 4. 最初の30日の投稿計画

### 4-1. 投稿の型（4つ）

| 型 | 中身 | 狙い | 使うSNS |
|---|---|---|---|
| **A. どっちクイズ** | 「同じお願い、AとBどっちの頼み方がうまくいく？ 返信でAかBで答えてね」→ 夜に答え合わせを返信で追加 | 返信を集める（Threadsで一番効く） | Threads・X |
| **B. やってみた** | 「〇〇をAIに頼んでみた」：頼み方 → 結果 → スライムの一言 | 「へぇ」と保存 | Threads・Instagramカルーセル・X |
| **C. 3秒テンプレ** | コピペで使える頼み方を1つだけ（例：「メールを角が立たないように直して」） | 保存・シェア | Instagramカルーセル・Threads |
| **D. 海外の仕組み特集（週1）** | 確認済みのネタ帳から1つ。最後に「日本だとどうなる？」 | 今のファンとB2Bの見込み客をつなぎ止める | 全SNS |

- リール（月・水・金）は型Bを縦動画にしたもの。今ある `scripts/make_reel.sh`（スライド→mp4）をそのまま使う。**毎回同じ構成・同じAI音声だけにしない**（YouTubeの「大量生産」ルールと同じ考え方がMetaにもあるため）。スライムの一言や色の変化で毎回変化をつける。

### 4-2. 頻度と時刻（初期値。2週目から実績で調整）

| SNS | 1日の本数 | 時刻 | 1週間の内訳 |
|---|---|---|---|
| Threads | 3本 | 8:00（C）／12:15（A）／20:30（B、Aの答え合わせも） | A×7・B×7・C×6・D×1 |
| Instagram | 1本 | 19:00 | リール×3（月水金）・カルーセル×3（火木土）・日曜は休み、またはD |
| X | 2本 | 7:30／21:00 | Threadsの A と B を短くしたもの。リンクなし |
| Bluesky | Threadsと同じ | Threadsの直後 | 転記 |

30日の合計：Threads 約90本、Instagram 約26本、X 約60本。

### 4-3. 週ごとの進め方

| 週 | やること | 判断 |
|---|---|---|
| 1週目（1〜7日） | 4つの型を全部試す。オーナーは手で投稿しない前提なので、トークン登録が済んだThreads・Blueskyから `AUTO_POST: true`（品質管理を通ったものだけAPI投稿）に切り替える。Instagram・Xは準備ができしだい追加 | 7日目：型ごとの平均表示と返信数を比べる |
| 2週目（8〜14日） | 伸びた型を増やし、伸びない型を減らす。Instagramのリールを開始（動画の置き場が決まっていれば） | **14日目：続けるか切り替えるかの判断（下の基準）** |
| 3週目（15〜21日） | 一番伸びた型を1日2本に。noteの商品へのプロフィールリンクを開始 | 21日目：投稿時刻の見直し |
| 4週目（22〜30日） | 伸びた投稿の「続編」「別の頼み方」を作る | 30日目：2か月目の方針を決める |

### 4-4. 伸びたかを判断する基準

数字は `data/metrics.md` に週1で記録する（Threads・InstagramはAPIのインサイトで取れる。Xは読み取りも有料なので、自分の投稿の数字だけを週1回取る）。

| 時点 | 指標 | 「伸びている」 | 「伸びていない」→ 対応 |
|---|---|---|---|
| 毎日 | 1投稿の表示数 | 型ごとの中央値を出す | 同じ型が5本続けて中央値の半分以下 → その型をやめる |
| 7日目 | Threadsの1投稿あたり返信数 | 平均1件以上 | 平均0件 → クイズの問いかけを短く・答えやすく（AかBだけ）する |
| 14日目 | Threadsのフォロワー | **30人以上** | **30人未満 → テーマを「雑学クイズ×スライム」に切り替える** |
| 14日目 | 表示数の合計（全SNS） | 1週目より2週目が多い | 減った → 時刻と型を見直す |
| 30日目 | フォロワー合計（全SNS） | **150人以上**（目安。第1回の目標「4週間で300人」は、ゼロからだと強気すぎるので下げる） | 50人未満 → 2か月目にTikTokの審査申請を検討 |
| 30日目 | プロフィールのリンクのクリック | 30回以上（Threadsのリンク分析で確認） | 0〜数回 → 商品とテーマがずれている。収益化AIと相談 |

※ 上の目標値は、調べた抜粋に「ゼロから1か月でどれくらい伸びるか」の信頼できる数字がなかったので、**戦略AIの見込み**。1週目の実績で直す。

---

## 5. オーナーへの依頼（1回にまとめる）

1. **Threads**：アカウント作成（Instagramのアカウントから作る）と、Meta開発者アプリのトークン登録
2. **Instagram**：プロアカウントへの切り替え、Facebookページとの連携（必要なら）、トークン登録、**画像・動画を置く公開URL**の用意（無料で置ける場所は社長と相談。要確認）
3. **X**：APIのクレジットを少しだけ前払い（$5程度で2か月以上もつ見込み）、自動化アカウントのラベル設定
4. **Bluesky**：アカウント作成と、アプリパスワードの登録
5. プロフィールに「AIが運営しています」と書く（文面はAIが用意）

## 6. 確かでない点（要確認のまとめ）

- XのAPIの最新料金（Developer Consoleで確認）と、自動化ラベルが必須かどうか
- Instagram APIの投稿上限（50件か100件か）、Facebookページ連携が必須かどうか、無料で使える動画の公開置き場
- Instagramの「トライアルリール」がフォロワー1,000人未満で使えるか
- Threadsで、AI生成の投稿にラベルが必要か・リーチに影響するか
- YouTube APIの「審査前は非公開」が今も同じか
- Blueskyの日本の利用者数
- 「AIの使い方」ジャンルが2026年の日本のThreadsで伸びやすいという具体的なデータ（今回は見つからず、一般的な見込み）

---

## 出典（WebSearchの抜粋で確認したもの）

- X API料金：[OpenTweet: Is the X API free in 2026](https://opentweet.io/answers/is-the-x-api-free-in-2026)、[Zernio: X API Pricing 2026](https://zernio.com/blog/twitter-api-pricing)、[OpenTweet: X API pay-per-use](https://opentweet.io/how-to/x-api-pay-per-use-explained)
- X 自動化ルール：[X Help: Automation rules](https://help.x.com/en/rules-and-policies/x-automation)、[OpenTweet: Twitter automation rules 2026](https://opentweet.io/blog/twitter-automation-rules-2026)、[OpenTweet: purge](https://opentweet.io/answers/did-x-suspend-my-bot-in-the-purge)
- X アルゴリズム：[PostEverywhere: How the X algorithm works](https://posteverywhere.ai/blog/how-the-x-twitter-algorithm-works)、[OpenTweet: why your X account is not growing](https://opentweet.io/blog/why-your-x-account-is-not-growing)
- Threads API：[gori.me: Threads API一般公開](https://gori.me/?p=153878)、[Meta: Threads API overview](https://developers.facebook.com/docs/threads/overview)、[Web担当者Forum（2025/10）](https://webtan.impress.co.jp/e/2025/10/23/50189)
- Threads 国内：[Impress Watch: Threads 3周年](https://www.watch.impress.co.jp/docs/news/2121668.html)、[stock-sun: Threads企業アカウント](https://stock-sun.com/column/threads-kigyo-account/)、[tatap: Threadsの伸ばし方](https://tatap.jp/knowledge/how-to-extend-threads/)
- Threads リンク：[Social Media Today](https://www.socialmediatoday.com/news/meta-says-link-posts-ranked-properly-threads-reach/750126/)、[GIGAZINE: プロフィールにリンク5個](https://gigazine.net/gsc_news/en/20250516-threads-add-5-links-profiles)
- Instagram API：[Meta: Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing)、[Meta: Instagram Platform changelog](https://developers.facebook.com/documentation/instagram-platform/changelog)、[PostProxy: Post to Instagram via API](https://postproxy.dev/blog/post-to-instagram-via-api/)
- Instagram AI・転載：[TechCrunch 2026/8/31: undisclosed AI profiles](https://techcrunch.com/2026/08/31/instagram-puts-new-limits-on-undisclosed-ai-profiles/)、[TechCrunch 2026/4/30: content aggregators](https://techcrunch.com/2026/04/30/instagram-restricts-reach-of-content-aggregators-in-new-crackdown/)、[TechCrunch 2025/7/14: Facebook unoriginal content](https://techcrunch.com/2025/07/14/following-youtube-meta-announces-crackdown-on-unoriginal-facebook-content)
- Instagram トライアルリール：[Publer](https://publer.com/blog/instagram-trial-reels-guide/)、[Outfy](https://outfy.com/blog/instagram-trial-reels)、[Tubefilter](https://www.tubefilter.com/2025/01/23/instagram-trial-reels-growth-hacking-creator-economy/)
- TikTok API：[TikTok: Content Sharing Guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines)、[bundle.social: TikTok API approval](https://bundle.social/blog/tiktok-api-approval)
- TikTok AIラベル：[NBC News](https://www.nbcnews.com/tech/tech-news/tiktok-will-automatically-label-ai-generated-content-rcna151446)
- YouTube：[Plagiarism Today: inauthentic content](https://www.plagiarismtoday.com/2025/07/08/youtube-targets-inauthentic-content/)、[Gulf News](https://gulfnews.com/technology/youtube-updates-monetisation-policies-ai-and-repetitive-content-ban-begins-july-15-1.500192660)、[Google: quota cost](https://developers.google.com/youtube/v3/determine_quota_cost)、[KeyShot: YouTube Service](https://keyshot.atlassian.net/wiki/spaces/DD/pages/3804631595/DC+6.0+YouTube+Service)
- note：[noteヘルプ: note API](https://www.help-note.com/hc/ja/articles/63304278903321)、[uravation: note自動投稿](https://uravation.com/media/claude-code-note-auto-post/)
- LINE VOOM：[LINEヤフー for Business 2026/7/15](https://www.lycbiz.com/jp/news/line-official-account/20260715)、[同 2026/7/30](https://www.lycbiz.com/jp/news/line-official-account/20260730/)
- Bluesky：[Bluesky Docs: bots](https://docs.bsky.app/docs/starter-templates/bots)、[Bluesky Docs: rate limits](https://docs.bsky.app/docs/advanced-guides/rate-limits)、[Bluesky Docs: developer guidelines](https://docs.bsky.app/docs/support/developer-guidelines)、[Thunderbit: Bluesky統計](https://thunderbit.com/ja/blog/bluesky-statistics)
- 日本の利用者数：[Meltwater: SNS利用者数ランキング](https://www.meltwater.com/jp/blog/social-media-users-world-ranking)、[PR TIMES: 2026年度 SNS利用動向調査](https://prtimes.jp/main/html/rd/p/000000030.000019182.html)、[comnico: SNS利用者数](https://www.comnico.jp/we-love-social/sns-users)

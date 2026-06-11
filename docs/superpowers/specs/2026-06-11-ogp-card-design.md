# リンクカード（OGP）改善 設計

日付: 2026-06-11
状態: 承認済み

## 目的

noshi.me のリンクカードが「テキストのみ・説明文が機械的」で見栄えが悪い。
OGP 画像と整った文言で、SNS・チャットでシェアされたときの第一印象を上げる。

## 決定事項（ビジュアルコンパニオンで選定）

- **画像**: A案「和ミニマル」— 生成り（#F3EEE2）背景＋のし紙風枠線＋朱印「の」（favicon と同モチーフ）
  ＋セリフ体ロゴ「noshi」＋タグライン「贈りものの記録と、お返し選び。」。1200×630 PNG（約30KB）を
  `frontend/public/ogp.png` に静的配置（Pillow＋Noto フォントで生成済みの実物をコミット）
- **説明文**: 情緒型「いただいた気持ちを、忘れない。贈りものの記録からお返し選びまで、noshi がそっとお手伝いします。」
  （旧:「家族・親族・友人との贈答（もらった／あげた）をAIで一元管理する noshi。」— 機械的な挿入句と
  「一元管理」の堅さを解消）
- **タイトル**: `noshi｜贈りものの記録と、お返し選び`（<title> と og:title 共通。タブ表示も変わる）

## 実装

`frontend/index.html` の head に OGP/Twitter メタタグ一式を追加（og:type/site_name/title/description/
url/image/image:width/image:height、twitter:card=summary_large_image）。og:image は絶対URL
`https://noshi.me/ogp.png`。description メタも同文に更新。

SPA だが OGP クローラは静的 HTML を読むため index.html への直書きで足りる。
ページ別 OGP（動的生成）はスコープ外（YAGNI — 公開ページは実質トップのみ）。

## 検証

- ローカル: `npm run build` 後の dist/index.html にタグが乗ること・/ogp.png が dist に入ること
- デプロイ後: `curl -s https://noshi.me/ | grep og:` でタグ確認、https://noshi.me/ogp.png が 200。
  LINE/Slack/X はカードをキャッシュするため、反映確認は新規URL扱いになるパラメータ付き
  （例: noshi.me/?v=2）で行うか、各サービスのキャッシュ更新を待つ

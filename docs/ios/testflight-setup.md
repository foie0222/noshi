# TestFlight 配信パイプライン セットアップ手順（#196）

物理 Mac を使わず、GitHub Actions の macOS runner で**署名つきアーカイブ → TestFlight 配信**を行うための手順。署名は **App Store Connect API キー（.p8）による自動署名**で行うため、配布証明書(.p12)やプロビジョニングプロファイルの手動管理・fastlane match は不要。

ワークフロー実体: `.github/workflows/ios-release.yml`（手動実行 or `ios-v*` タグ push で起動）。

---

## 前提（この順に）

### 0. #193 をマージ
`frontend` に Capacitor 一式（`capacitor.config.ts`・`@capacitor/*`）が入っていること。

### 1. App ID を登録（#210）
[Developer ポータル](https://developer.apple.com/account/resources/identifiers/list) → Identifiers → ＋ → App IDs → App
- Bundle ID（Explicit）: **`me.noshi.app`**（`capacitor.config.ts` の `appId` と一致）
- Capabilities: 後で **Push Notifications**（#205）を使うので有効化しておくとよい

### 2. App Store Connect にアプリレコード作成（#210）
[App Store Connect](https://appstoreconnect.apple.com) → マイApp → ＋ → 新規 App
- プラットフォーム: iOS / 名前: noshi / 主言語: 日本語 / Bundle ID: `me.noshi.app` / SKU: 任意（例 `noshi-ios`）

### 3. App Store Connect API キーを発行
[ASC → ユーザーとアクセス → 統合 → App Store Connect API](https://appstoreconnect.apple.com/access/integrations/api)
- 「チームキー」を生成。アクセス権: **App Manager**（TestFlight 配信・署名管理に十分）
- 生成時に **`.p8` ファイルをダウンロード**（再ダウンロード不可。厳重保管）
- 控える3点: **Key ID** / **Issuer ID**（ページ上部）/ `.p8` の中身

---

## GitHub Secrets を登録
リポジトリ → Settings → Secrets and variables → Actions → New repository secret

| Secret 名 | 値 |
| --- | --- |
| `ASC_KEY_ID` | API キーの Key ID（例: `ABCD1234EF`） |
| `ASC_ISSUER_ID` | Issuer ID（UUID 形式） |
| `ASC_API_KEY_P8` | `.p8` ファイルの**中身そのまま**（`-----BEGIN PRIVATE KEY-----` から `-----END PRIVATE KEY-----` まで全行） |
| `APPLE_TEAM_ID` | チームID `63AST5A8VY` |

> `.p8` は改行を保ったまま貼り付ける。GitHub Secrets は複数行を保持できる。

---

## 実行
1. Actions → **iOS Release (TestFlight)** → Run workflow（手動）。
   - もしくは `git tag ios-v0.1.0 && git push origin ios-v0.1.0`。
2. 成功すると数十分後に App Store Connect → TestFlight にビルドが現れる（処理中→処理完了）。
3. 初回は**輸出コンプライアンス**の質問が出る場合あり。`Info.plist` に `ITSAppUsesNonExemptEncryption=NO`（#213）を入れておけば回避できる（`ios/` をコミットするフェーズで反映）。

## ビルド番号
TestFlight はビルド番号の重複を拒否するため、ワークフローは **GitHub Actions の run 番号**を `agvtool` でビルド番号に設定する。マーケティングバージョン（1.0.0 等）は別途 `Info.plist`/`MARKETING_VERSION` で管理（`ios/` コミット時に整備）。

## 既知の注意・次段
- 本ワークフローは **Secrets と App ID(#210) が揃うまで成功しない**（揃うまでは手動実行時のみ起動し、PR や通常 push は汚さない）。
- 初回実行は署名アセットの自動生成や ASC 側の整合で**追加調整が要る場合がある**（`-allowProvisioningUpdates` での配布証明書自動作成など）。緑化まで CI ログを見て数回反復する想定。
- 署名を伴う本番アーカイブを安定させるため、近い将来 **`ios/` プロジェクトをコミット**し、`Info.plist`（カメラ権限 #203・輸出 #213・バージョン）を版管理下に置くのが望ましい（現状は CI 都度生成）。
- 外部テスター配信には **Beta App Review**（各バージョン初回）が必要（#215）。

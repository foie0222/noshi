# アプリ内アカウント削除（App Store Guideline 5.1.1(v) 対応）

関連 Issue: #198 / Epic #192 / 既存実装: #118

App Store Review Guideline **5.1.1(v)** は「アカウント作成があるアプリは、アプリ内からの恒久的なアカウント削除を提供すること（Web 誘導・問い合わせのみは不可）」を要求する。本書は noshi の実装が同要件を満たすことを、実装箇所と削除範囲とともに記録する（審査レビューノート #212 の根拠資料）。

- 出典: https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage
- 補足: https://developer.apple.com/support/offering-account-deletion-in-your-app/

## 1. アプリ内導線（in-app で開始〜完了）

| 要件 | 実装 | 箇所 |
| --- | --- | --- |
| 見つけやすい場所に削除導線 | マイページ「アカウント」カードに「アカウントを削除」（危険導線） | `frontend/src/App.tsx`（マイページのアカウントカード） |
| 削除前の確認 | 確認ダイアログで「取り消せない」「記録・画像がすべて消える」「共有台帳は家族に引き継がれる」を明示 | `frontend/src/App.tsx` `doDeleteAccount()` |
| アプリ内で完了 | `DELETE /api/account` 呼び出し → サインアウト → 「アカウントを削除しました」通知。Web 誘導なし | `frontend/src/App.tsx` `doDeleteAccount()` / `frontend/src/api.ts` `deleteAccount` |
| 恒久削除（無効化ではない） | Cognito ユーザー本体を `admin_delete_user` で削除、本人データを物理削除 | `backend/app/main.py` `delete_account` ルート |

## 2. 削除範囲（実装と一致）

`backend/app/services.py` の `delete_account()` / `_purge_household()` が以下を削除する。

- **Cognito ユーザー本体**: `admin_delete_user`（`NOSHI_COGNITO_POOL_ID` 設定時。`backend/app/main.py`）
- **本人の世帯メンバーシップ**: `delete_membership`
- **世帯の最後の利用者だった場合は世帯データを完全消去**（`_purge_household`）:
  - 台帳レコード（もらった/あげた）
  - ご祝儀袋画像（S3 / `images.delete(image_key)`）
  - お返しイベント（期限・お返し記録）
  - 相手（party）情報
  - 世帯独自の用途マスタ・続柄マスタ
  - 世帯本体
- **監査ログ**: `delete_account` / `transfer_ownership` を記録（A09）

## 3. 世帯共有データの帰属ルール（決定事項）

noshi は世帯（家族）単位で台帳を共有するため、削除時の共有データ帰属を以下に確定する（実装済み）。

- **家族が他に残る場合**: 台帳は「家族の資産」として**残す**。削除者が owner だった場合は、最古参メンバーへ **owner を自動移譲**（`transfer_ownership`）。削除者のメンバーシップのみ外す。
- **削除者が世帯の最後の利用者の場合**: 世帯データを**完全消去**（`_purge_household`）。

この方針により「自分のアカウントは消えるが、家族が共同で築いた記録は家族側に残る」という共有プロダクトとして自然な挙動を保証する。

## 4. プライバシーポリシー / 利用規約への反映

- 利用規約 第9条（退会）: 「『アカウントを削除』からいつでも退会できる」旨を明記（`frontend/src/legal.ts`）。
- プライバシー文言: 「退会時、共有中の世帯台帳は残るご家族に引き継がれ、最後の利用者の場合は世帯データを完全に消去する」旨を明記（`frontend/src/legal.ts`）。
- 保持/削除・同意撤回手段のポリシー記載の最終確認は #200 で扱う。

## 5. 未確定（人間の判断が必要 / 別Issue）

実装の追加可否は製品判断のため本書では確定しない。

- **削除前の再認証（パスワード / SiwA 再入力）**: 現状は確認ダイアログのみ。Apple は再認証を必須化していないが、誤操作・なりすまし対策として追加するかは UX とのトレードオフ。→ #198 で判断。
- **削除前のデータエクスポート案内**: 削除フロー直前にエクスポートを促すかは #119（データエクスポート）と対で検討。

## 6. macOS での実機検証（残作業）

本書および既存実装は Linux 環境（backend pytest / frontend vitest）で検証済み。ただし「iOS アプリ内のみで削除を開始〜完了できる」ことの**実機/シミュレータ確認は macOS + Xcode が必要**で未実施。Capacitor 内包後（#193）に、マイページ→削除→サインオフまでを実機で確認すること。

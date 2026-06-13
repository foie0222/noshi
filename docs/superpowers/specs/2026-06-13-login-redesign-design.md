# ログイン画面リデザイン設計

- 日付: 2026-06-13
- 対象: `frontend/src/App.tsx`（ログイン画面ヘッダ）, `frontend/src/styles.css`
- Issue/背景: ログイン画面のタグラインが旧方針のまま（「贈答を、ちゃんと続けられる。」）で、対外コピー（OGP）の「大切な人との縁を、長く美しく。」と不一致。

## 目的

ログイン画面のヘッダを、サービスの3層情報で一貫させる。スコープはコピー刷新＋ビジュアルの底上げ（既存の和フラット路線を磨く範囲。配色・構成の全面刷新はしない）。

## 一貫させる3層（確定）

| 層 | 文言 | 既存の一致先 |
|---|---|---|
| サービス名 | noshi（ロゴ ＋ N O S H I） | ロゴ・favicon |
| 何をやるか（説明） | 贈りものの記録と、お返し選び | `<title>` の `noshi｜贈りものの記録と、お返し選び` |
| コンセプト（情緒） | 大切な人との縁を、長く美しく。 | `index.html` の meta description / og:description |

このリデザインで、**ページタイトル・OGP・ログイン画面の3箇所がすべて同じ言葉で揃う**。`index.html` と OGP は既に上記の文言なので変更不要（一致確認のみ）。

## ヘッダの構成（確定: ヘッダ案C「コンセプト主役＋区切り線」）

上から順に:

1. ロゴ（`<Logo variant="full" size={40} />`）— 現状のまま
2. `N O S H I`（`.brand-en`）— 現状のまま
3. **大切な人との縁を、長く美しく。**（コンセプト・明朝・主役）
4. 細い区切り線（淡いサンド色・幅 ~38px）
5. 贈りものの記録と、お返し選び（説明・小・ゴシック・サブ色）

旧 `.muted` の1行「贈答を、ちゃんと続けられる。」は廃止。

## 実装詳細

### `frontend/src/App.tsx`（ログイン画面ヘッダ, 現 771–779 行付近）

現状:
```tsx
<div className="brand"><Logo variant="full" size={40} /></div>
<div className="brand-en">N O S H I</div>
<p className="muted" style={{ textAlign: "center" }}>
  贈答を、ちゃんと続けられる。
</p>
```

変更後:
```tsx
<div className="brand"><Logo variant="full" size={40} /></div>
<div className="brand-en">N O S H I</div>
<p className="login-concept">大切な人との縁を、長く美しく。</p>
<div className="login-divider" aria-hidden="true" />
<p className="login-desc">贈りものの記録と、お返し選び</p>
```

### `frontend/src/styles.css`（新クラス3つを追加。`.brand-en` の直後あたり）

```css
.login-concept {
  font-family: var(--font-display);
  font-weight: var(--fw-bold);
  font-size: var(--fs-h3);          /* 18px。明朝で主役だが控えめに上品に */
  color: var(--text-body);
  text-align: center;
  line-height: var(--lh-relaxed);
  margin: var(--space-3) 0 0;       /* 12px */
}
.login-divider {
  width: 38px;
  height: 1px;
  background: var(--border-default);
  margin: 12px auto;
}
.login-desc {
  font-family: var(--font-body);
  font-size: var(--fs-sm);          /* 13px */
  color: var(--text-sub);
  text-align: center;
  letter-spacing: var(--ls-wide);
  margin: 0 0 4px;
}
```

- 既存トークンのみ使用。新しい色・影・グラデは足さない（フラット方針維持）。`--space-3`(12px) は実在確認済み。

## 検証

- 見た目の変更のため `biome` / `tsc` / `vite build` で担保。
- 文言の自動テストは追加しない（過剰）。
- 実ブラウザ（本番デプロイ後）でヘッダの3層表示と、スマホ幅での折り返しを確認。

## 非対象（YAGNI）

- ログインカード（Google/メール/LINE）のレイアウト変更はしない。
- 配色・背景・全面刷新（ヘッダ案の全面刷新＝C案検討時のB案演出）はしない。
- `index.html` / OGP の変更はしない（既に一致）。

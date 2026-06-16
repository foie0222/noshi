# お返し品の品目カテゴリ提案 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** お返し品の提案画面に品目カテゴリのタブを追加し、厳選ピックが外れたときに「おすすめ」から品目で探し直せる逃げ道を作る。

**Architecture:** 非破壊の並行追加。既存の用途×予算バケツ（`BUCKET#<用途>#<予算>`）と配信パスは無改造で「おすすめ」既定タブとして残す。新たに `BUCKET#<tone>#<品目>#<予算>`（tone=cele/mourn）の品目バケツと、空タブを防ぐマニフェスト（`MANIFEST#<tone>#<予算>`）を日次バッチで作り、配信は任意 `category` パラメータで品目バケツに切り替える。バッチは1日2回→1回（JST 9:00）に削減。

**Tech Stack:** Python 3.12 / FastAPI / pytest（backend）、DynamoDB（NoshiCatalogTable）、React + Vite + TypeScript（frontend）、AWS CDK（infra）。設計の正本: `docs/superpowers/specs/2026-06-17-return-gift-categories-design.md`。

---

## File Structure

作成・変更するファイルと責務:

- `backend/app/catalog/buckets.py`（変更）: 品目タクソノミ（トーン別）と派生テーブル、`tone_slug`/`item_bucket_slug` を追加。
- `backend/app/catalog/scoring.py`（変更）: `passes_gate` を品目スラッグ（`mourn#*`）でも弔事NGを使うよう拡張。
- `backend/app/catalog/curation.py`（変更）: `build_user_prompt` に品目バケツ用のトーン＋品目の文面分岐を追加。
- `backend/app/catalog/store.py`（変更）: マニフェストの `write_manifest`/`read_manifest` を追加。
- `backend/app/catalog/job.py`（変更）: 品目バケツの処理・ジャンル統合・マニフェスト書き込みを追加。
- `backend/app/catalog/adapter.py`（変更）: `suggest(category=...)` と `available_categories`、`_band_of_row` の4セグメント対応。
- `backend/app/ports.py`（変更）: `GiftCatalogPort` に `category` 引数と `available_categories` を追加、`GiftCatalogMock` を追従。
- `backend/app/services.py`（変更）: `suggest_returns` に `category` 素通し、`return_categories` を追加。
- `backend/app/main.py`（変更）: `/api/events/{id}/suggestions` に `category` クエリと `categories` レスポンスを追加。
- `backend/app/catalog/__main__.py`（変更）: スモークCLIが品目スラッグも受け付ける。
- `frontend/src/types.ts`（変更）: `SuggestCategory` 型を追加。
- `frontend/src/api.ts`（変更）: `suggestions` に任意 `category` 引数、レスポンス型に `categories`。
- `frontend/src/App.tsx`（変更）: 提案画面にタブ（チップ）UIと状態・切替を追加。
- `frontend/src/styles.css`（変更）: タブ（チップ）のスタイル。
- `infra/cdk/lib/catalog-batch-stack.ts`（変更）: スケジュールを JST 9:00 の1日1回に。
- 各 `backend/tests/test_catalog_*.py`・`backend/tests/test_main.py`（変更/追加）: 上記のテスト。

---

## Task 0: 環境準備（worktree のテスト実行基盤）

worktree `feat/return-gift-categories`（`/home/inoue-d/dev/noshi-wt-retcat`）で backend テストと frontend ビルドが通る状態を作る。

**Files:** なし（環境のみ）

- [ ] **Step 1: backend の venv を用意**

メインリポジトリの venv を流用する（既存の運用パターン）。

Run:
```bash
ln -sfn /home/inoue-d/dev/noshi/backend/.venv /home/inoue-d/dev/noshi-wt-retcat/backend/.venv
cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest -q tests/test_catalog_adapter.py 2>&1 | tail -5
```
Expected: 既存テストが PASS（環境が動くことの確認）。

- [ ] **Step 2: frontend の依存を用意**

Run:
```bash
cd /home/inoue-d/dev/noshi-wt-retcat/frontend && npm ci --ignore-scripts 2>&1 | tail -3
node_modules/.bin/tsc --noEmit 2>&1 | tail -5
```
Expected: `tsc --noEmit` がエラーなしで完了。

注: 以降のテストコマンドは backend を `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest ...`、frontend を `node_modules/.bin/tsc` / `node_modules/.bin/biome` で実行する。コミットは pre-commit が venv/node_modules を要求して落ちる場合があるため、内容を biome/pytest で個別確認のうえ必要なら `--no-verify` を使う（既存運用と同じ）。

---

## Task 1: 品目タクソノミ定義（buckets.py）

トーン別の品目カテゴリと、配信・バッチが引く派生テーブル、トーン接頭辞ヘルパーを追加する。

**Files:**
- Modify: `backend/app/catalog/buckets.py`
- Test: `backend/tests/test_catalog_buckets.py`

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_catalog_buckets.py` の末尾に追記:

```python
def test_品目タクソノミの派生テーブルがトーン別に揃う():
    from app.catalog.buckets import (
        ITEM_CATEGORIES,
        ITEM_CATEGORY_KEYWORDS,
        ITEM_CATEGORY_LABELS,
    )

    assert [c for c, _l, _k in ITEM_CATEGORIES["cele"]] == [
        "sweets", "gourmet", "drink", "towel", "tableware", "sake", "catalog",
    ]
    assert [c for c, _l, _k in ITEM_CATEGORIES["mourn"]] == [
        "drink", "food", "towel", "daily", "catalog",
    ]
    # 派生テーブルは "tone#cat" をキーにする
    assert ITEM_CATEGORY_KEYWORDS["cele#towel"] == "内祝い タオル ギフト"
    assert ITEM_CATEGORY_LABELS["mourn#daily"] == "洗剤・日用品"
    assert len(ITEM_CATEGORY_KEYWORDS) == 12


def test_tone_slug_と_item_bucket_slug():
    from app.catalog.buckets import item_bucket_slug, tone_slug

    assert tone_slug("出産祝い") == "cele"
    assert tone_slug("香典") == "mourn"
    assert item_bucket_slug("cele", "towel") == "cele#towel"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_buckets.py -q`
Expected: FAIL（`ImportError`/`cannot import name 'ITEM_CATEGORIES'`）。

- [ ] **Step 3: 実装する**

`backend/app/catalog/buckets.py` の `bucket_pk` 定義の後（ファイル末尾）に追記:

```python
# --- 品目カテゴリ（スペック 2026-06-17）。slug は f"{tone}#{cat}"、tone は cele/mourn ---
# tone -> [(cat_slug, 表示名, 楽天検索キーワード), ...]（リスト順がタブ表示順）
ITEM_CATEGORIES: dict[str, list[tuple[str, str, str]]] = {
    "cele": [
        ("sweets", "スイーツ・お菓子", "内祝い 洋菓子 焼き菓子"),
        ("gourmet", "グルメ・食品", "内祝い グルメ 食品"),
        ("drink", "飲料", "内祝い コーヒー 日本茶 ギフト"),
        ("towel", "タオル・寝具", "内祝い タオル ギフト"),
        ("tableware", "食器・キッチン", "内祝い 食器 ギフト"),
        ("sake", "お酒", "内祝い 酒 ギフト"),
        ("catalog", "カタログギフト", "内祝い カタログギフト"),
    ],
    "mourn": [
        ("drink", "飲料", "香典返し 緑茶 コーヒー"),
        ("food", "食品", "香典返し 海苔 乾物"),
        ("towel", "タオル・寝具", "香典返し タオル"),
        ("daily", "洗剤・日用品", "香典返し 洗剤 日用品"),
        ("catalog", "カタログギフト", "香典返し カタログギフト"),
    ],
}

# 配信・バッチ用の派生テーブル（slug = "tone#cat"）
ITEM_CATEGORY_KEYWORDS: dict[str, str] = {
    f"{tone}#{cat}": kw for tone, rows in ITEM_CATEGORIES.items() for cat, _label, kw in rows
}
ITEM_CATEGORY_LABELS: dict[str, str] = {
    f"{tone}#{cat}": label for tone, rows in ITEM_CATEGORIES.items() for cat, label, _kw in rows
}
# 品目バケツの楽天ランキングAPIジャンルID。当面は総合ランキング（None=トレンド寄与半減）。
# 実機でカテゴリ上位の最頻ジャンルを採取でき次第、個別IDに差し替える。
RAKUTEN_GENRE_BY_ITEM_CATEGORY: dict[str, str | None] = dict.fromkeys(ITEM_CATEGORY_KEYWORDS, None)


def tone_slug(purpose: str) -> str:
    """用途 → 品目バケツのトーン接頭辞（cele=慶事 / mourn=弔事）。"""
    from app.domain.tone import tone_of

    return "mourn" if tone_of(purpose) == "mourning" else "cele"


def item_bucket_slug(tone: str, cat: str) -> str:
    """品目バケツの slug（store/adapter の slug 引数として使う）。"""
    return f"{tone}#{cat}"
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_buckets.py -q`
Expected: PASS（既存テストも含め全 PASS）。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/catalog/buckets.py backend/tests/test_catalog_buckets.py
git commit -m "feat(catalog): 品目タクソノミ（トーン別）と派生テーブルを追加"
```

---

## Task 2: 弔事ゲートを品目スラッグ対応にする（scoring.py）

`passes_gate` は現状 `slug == "koden"` のときだけ弔事NGリストを使う。品目バケツ（`mourn#*`）でも弔事NGを使うようにする。

**Files:**
- Modify: `backend/app/catalog/scoring.py:46-49`
- Test: `backend/tests/test_catalog_scoring.py`

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_catalog_scoring.py` の末尾に追記:

```python
def test_弔事品目スラッグでは弔事NGワードで弾く():
    from app.catalog.scoring import passes_gate

    base = {
        "review_count": 100,
        "rating": 4.5,
        "availability": 1,
        "affiliate_url": "https://hb.afl.rakuten.co.jp/x",
    }
    # mourn# 系は koden と同じく祝い向け語を弾く
    assert passes_gate({**base, "title": "出産御祝ギフト"}, "mourn#food") is False
    # 慶事品目では祝い向け語は通り、弔事向け語を弾く
    assert passes_gate({**base, "title": "上質タオルセット"}, "cele#towel") is True
    assert passes_gate({**base, "title": "香典返し 緑茶"}, "cele#towel") is False
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_scoring.py -q`
Expected: FAIL（`passes_gate({...}, "mourn#food")` が True を返す）。

- [ ] **Step 3: 実装する**

`backend/app/catalog/scoring.py` の `passes_gate` 内、NGリスト選択を変更:

変更前:
```python
    title = item.get("title", "")
    ng = _NG_KODEN if slug == "koden" else _NG_CELEBRATION
```
変更後:
```python
    title = item.get("title", "")
    is_mourning = slug == "koden" or slug.startswith("mourn#")
    ng = _NG_KODEN if is_mourning else _NG_CELEBRATION
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_scoring.py -q`
Expected: PASS。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/catalog/scoring.py backend/tests/test_catalog_scoring.py
git commit -m "feat(catalog): 弔事ゲートを品目スラッグ(mourn#*)でも適用"
```

---

## Task 3: 品目バケツ用のキュレーション文面（curation.py）

`build_user_prompt` は用途バケツ前提で「用途「○○」…」と書く。品目バケツ（slug に `#`）ではトーン＋品目の文面にする。用途バケツの出力は1バイトも変えない（既存テスト保護）。

**Files:**
- Modify: `backend/app/catalog/curation.py:13`（import）, `:56-82`（`build_user_prompt`）
- Test: `backend/tests/test_catalog_curation.py`

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_catalog_curation.py` の末尾に追記:

```python
def test_品目バケツのプロンプトはトーンと品目を伝える():
    from app.catalog.curation import build_user_prompt

    p = build_user_prompt("cele#towel", "5000-9999", _cands(), season_note="")
    assert "慶事" in p
    assert "タオル・寝具" in p
    assert "用途「" not in p  # 品目バケツでは用途表記にしない

    m = build_user_prompt("mourn#food", "5000-9999", _cands(), season_note="")
    assert "弔事" in m
    assert "食品" in m
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_curation.py -q`
Expected: FAIL（`"慶事" in p` が False、`"用途「" not in p` が False）。

- [ ] **Step 3: 実装する**

`backend/app/catalog/curation.py` の import 行を変更:

変更前:
```python
from app.catalog.buckets import CATEGORIES
```
変更後:
```python
from app.catalog.buckets import CATEGORIES, ITEM_CATEGORY_LABELS
```

`build_user_prompt` を変更:

変更前:
```python
    keyword = CATEGORIES.get(slug, slug)
    cands = [
```
変更後:
```python
    if "#" in slug:
        tone, _, _cat = slug.partition("#")
        tone_label = "弔事（香典返し）" if tone == "mourn" else "慶事（お祝い返し）"
        head = f"{tone_label}・品目「{ITEM_CATEGORY_LABELS.get(slug, slug)}」"
    else:
        head = f"用途「{CATEGORIES.get(slug, slug)}」"
    cands = [
```

同関数の return 文の先頭行を変更:

変更前:
```python
    return (
        f"用途「{keyword}」・価格帯 {band} 円のお返し品として適切な商品を、"
```
変更後:
```python
    return (
        f"{head}・価格帯 {band} 円のお返し品として適切な商品を、"
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_curation.py -q`
Expected: PASS（用途バケツの既存テスト `"香典返し" in p` 等も維持）。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/catalog/curation.py backend/tests/test_catalog_curation.py
git commit -m "feat(catalog): 品目バケツ用にキュレーション文面をトーン＋品目へ分岐"
```

---

## Task 4: マニフェストの読み書き（store.py）

(tone, 予算) ごとに在庫のある品目を記録/取得する。配信側が1件読むだけで出すべきタブが分かる。

**Files:**
- Modify: `backend/app/catalog/store.py`
- Test: `backend/tests/test_catalog_store.py`

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_catalog_store.py` の `FakeDdb` に `get_item` を足し、テストを追記する。

`FakeDdb` クラスに以下のメソッドと初期化を追加（`__init__` に `self.put_kw=[]` は不要。`put_item` は既存を流用）。`query` の下に追記:

```python
    def get_item(self, **kw):
        return getattr(self, "_get_item_result", {"Item": None})
```

テストを末尾に追記:

```python
def test_マニフェストを書いて読める():
    ddb = FakeDdb()
    store = CatalogStore(table_name="t", client=ddb)
    store.write_manifest("cele", "5000-9999", ["towel", "catalog"], NOW)

    put = ddb.puts[-1]
    assert put["Item"]["PK"]["S"] == "MANIFEST#cele#5000-9999"
    assert put["Item"]["SK"]["S"] == "MANIFEST"
    assert [e["S"] for e in put["Item"]["categories"]["L"]] == ["towel", "catalog"]

    # 読み出し（put した Item を get_item が返すよう仕込む）
    ddb._get_item_result = {"Item": put["Item"]}
    assert store.read_manifest("cele", "5000-9999", NOW) == ["towel", "catalog"]


def test_期限切れマニフェストは空を返す():
    from datetime import timedelta

    ddb = FakeDdb()
    store = CatalogStore(table_name="t", client=ddb)
    store.write_manifest("cele", "5000-9999", ["towel"], NOW)
    ddb._get_item_result = {"Item": ddb.puts[-1]["Item"]}
    # 書き込み48h後より先の now で読むと期限切れ
    assert store.read_manifest("cele", "5000-9999", NOW + timedelta(hours=49)) == []


def test_マニフェスト未登録は空を返す():
    ddb = FakeDdb()
    store = CatalogStore(table_name="t", client=ddb)
    assert store.read_manifest("mourn", "5000-9999", NOW) == []
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_store.py -q`
Expected: FAIL（`AttributeError: 'CatalogStore' object has no attribute 'write_manifest'`）。

- [ ] **Step 3: 実装する**

`backend/app/catalog/store.py` の `read_bucket` メソッドの直後（`# --- クリック計測 ---` の前）に追記:

```python
    # --- 品目マニフェスト ---

    def write_manifest(
        self, tone: str, band: str, categories: list[str], now: datetime
    ) -> None:
        """(tone, band) で在庫のある品目スラッグを総入れ替えで記録する。空でも上書きする。"""
        self._client.put_item(
            TableName=self.table_name,
            Item={
                "PK": {"S": f"MANIFEST#{tone}#{band}"},
                "SK": {"S": "MANIFEST"},
                "categories": {"L": [{"S": c} for c in categories]},
                "expiresAt": {"N": str(int((now + _ITEM_TTL).timestamp()))},
            },
        )

    def read_manifest(self, tone: str, band: str, now: datetime) -> list[str]:
        """(tone, band) の在庫ある品目スラッグを順序つきで返す。未登録/期限切れは空。"""
        r = self._client.get_item(
            TableName=self.table_name,
            Key={"PK": {"S": f"MANIFEST#{tone}#{band}"}, "SK": {"S": "MANIFEST"}},
        )
        item = r.get("Item")
        if not item:
            return []
        if int(item.get("expiresAt", {}).get("N", "0")) <= int(now.timestamp()):
            return []
        return [e.get("S", "") for e in item.get("categories", {}).get("L", [])]
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_store.py -q`
Expected: PASS。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/catalog/store.py backend/tests/test_catalog_store.py
git commit -m "feat(catalog): 品目マニフェストの読み書きを追加"
```

---

## Task 5: バッチで品目バケツを処理しマニフェストを書く（job.py）

`run_job` の既定（全実行）で、用途バケツ63に加えて品目バケツ84も処理し、(tone, band) ごとにマニフェストを書く。CLI 単一バケツ実行（categories 明示）は従来どおり。

**Files:**
- Modify: `backend/app/catalog/job.py:18`（import）, `:57-108`（`run_job`）
- Test: `backend/tests/test_catalog_job.py`

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_catalog_job.py` の `FakeStore` に `write_manifest` を追加し、既存カウントを更新、品目テストを追記する。

`FakeStore` を変更:

変更前:
```python
class FakeStore:
    def __init__(self):
        self.replaced = []
        self.items_by_bucket: dict = {}

    def replace_bucket(self, slug, band, items, job_run_id, now):
        self.replaced.append((slug, band, [i["item_code"] for i in items]))
        self.items_by_bucket[(slug, band)] = items
```
変更後:
```python
class FakeStore:
    def __init__(self):
        self.replaced = []
        self.items_by_bucket: dict = {}
        self.manifests: dict = {}

    def replace_bucket(self, slug, band, items, job_run_id, now):
        self.replaced.append((slug, band, [i["item_code"] for i in items]))
        self.items_by_bucket[(slug, band)] = items

    def write_manifest(self, tone, band, categories, now):
        self.manifests[(tone, band)] = list(categories)
```

既存のバケツ数アサーションを更新（用途63 + 品目84 = 147）:

- `test_全バケツを処理して書き込む`: `assert len(store.replaced) == 63` → `assert len(store.replaced) == 147`、`assert cur.calls == 63` → `assert cur.calls == 147`。
- `test_LLM失敗時は…`: `assert len(store.replaced) == 63` → `== 147`、`assert summary["llm_fallback"] == 63` → `== 147`。
- `test_LLMが空を返したら…`: `assert summary["llm_fallback"] == 63` → `== 147`。
- `test_時間バジェット超過後は…`: `assert len(store.replaced) == 63` → `== 147`。
- `test_検索が例外のバケツはスキップ…`: keyword 完全一致 `"香典返し"` で失敗するのは用途 koden の7価格帯のみ（品目キーワードは "香典返し 緑茶 コーヒー" 等で完全一致しない）。`assert summary["buckets_failed"] == 7` は不変、`assert len(store.replaced) == 56` → `assert len(store.replaced) == 140`（147−7）。

末尾に品目テストを追記:

```python
def test_品目バケツも処理してマニフェストを書く():
    store, cur = FakeStore(), FakeCurator()
    run_job(FakeRakuten(), cur, store, now=NOW, deadline=None)

    # 品目バケツが slug="tone#cat" 形式で書かれている
    item_slugs = {slug for slug, _band, _codes in store.replaced if "#" in slug}
    assert "cele#towel" in item_slugs
    assert "mourn#food" in item_slugs

    # (tone, band) ごとにマニフェストが書かれ、慶事は7品目・弔事は5品目（全件在庫ありのフェイク）
    assert store.manifests[("cele", "5000-9999")] == [
        "sweets", "gourmet", "drink", "towel", "tableware", "sake", "catalog",
    ]
    assert store.manifests[("mourn", "5000-9999")] == [
        "drink", "food", "towel", "daily", "catalog",
    ]
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_job.py -q`
Expected: FAIL（バケツ数が 63 のまま、`store.manifests` が空）。

- [ ] **Step 3: 実装する**

`backend/app/catalog/job.py` の import を変更:

変更前:
```python
from app.catalog.buckets import CATEGORIES, PRICE_BANDS, RAKUTEN_GENRE_BY_CATEGORY
```
変更後:
```python
from app.catalog.buckets import (
    CATEGORIES,
    ITEM_CATEGORY_KEYWORDS,
    PRICE_BANDS,
    RAKUTEN_GENRE_BY_CATEGORY,
    RAKUTEN_GENRE_BY_ITEM_CATEGORY,
)
```

`run_job` の冒頭、`categories = categories or CATEGORIES` の行を変更し、ジャンルマップを合成する:

変更前:
```python
    categories = categories or CATEGORIES
    bands = bands or PRICE_BANDS
```
変更後:
```python
    # 既定（Lambda 全実行）は用途バケツ＋品目バケツの両方。CLI は categories 明示で1バケツに絞る。
    categories = categories or {**CATEGORIES, **ITEM_CATEGORY_KEYWORDS}
    bands = bands or PRICE_BANDS
    genre_by_slug = {**RAKUTEN_GENRE_BY_CATEGORY, **RAKUTEN_GENRE_BY_ITEM_CATEGORY}
```

ランキング取得のジャンル参照を合成マップに変更:

変更前:
```python
    for slug in categories:
        genre = RAKUTEN_GENRE_BY_CATEGORY.get(slug)
```
変更後:
```python
    for slug in categories:
        genre = genre_by_slug.get(slug)
```

マニフェスト集計用の辞書を初期化（`failed = 0` 等の集計変数の近く、メインループ前に追加）:

```python
    manifest_acc: dict[tuple[str, str], list[str]] = {}
```

メインループ内、`store.replace_bucket(slug, band, top or [], job_run_id, now)` の直後に品目の在庫を集計する行を追加:

変更前:
```python
                store.replace_bucket(slug, band, top or [], job_run_id, now)
            except Exception:  # noqa: BLE001
```
変更後:
```python
                store.replace_bucket(slug, band, top or [], job_run_id, now)
                if "#" in slug:  # 品目バケツ: (tone, band) ごとに在庫ありの品目を記録
                    tone, _, cat = slug.partition("#")
                    manifest_acc.setdefault((tone, band), [])
                    if top:
                        manifest_acc[(tone, band)].append(cat)
            except Exception:  # noqa: BLE001
```

メインループ（`for slug, keyword …` の二重ループ）の後、`_emf(...)` の前にマニフェスト書き込みを追加:

```python
    for (tone, band), cats in manifest_acc.items():
        store.write_manifest(tone, band, cats, now)
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_job.py -q`
Expected: PASS。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/catalog/job.py backend/tests/test_catalog_job.py
git commit -m "feat(catalog): バッチで品目バケツを処理しマニフェストを書く"
```

---

## Task 6: 配信アダプタの品目対応（adapter.py）

`suggest` に任意 `category` を足し、品目バケツへ切り替える。`_band_of_row` を4セグメントのバケツPKに対応させる。`available_categories` を追加する。

**Files:**
- Modify: `backend/app/catalog/adapter.py:13`（import）, `:32-56`（`suggest`）, `:97-100`（`_band_of_row`）, 新メソッド追加
- Test: `backend/tests/test_catalog_adapter.py`

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_catalog_adapter.py` の `FakeStore` に `read_manifest` を足し、テストを追記する。

`FakeStore` を変更:

変更前:
```python
class FakeStore:
    def __init__(self, buckets):
        self.buckets = buckets  # {(slug, band): [rows]}
        self.clicks = []

    def read_bucket(self, slug, band, now):
        return self.buckets.get((slug, band), [])
```
変更後:
```python
class FakeStore:
    def __init__(self, buckets, manifests=None):
        self.buckets = buckets  # {(slug, band): [rows]}
        self.manifests = manifests or {}  # {(tone, band): [cat, ...]}
        self.clicks = []

    def read_bucket(self, slug, band, now):
        return self.buckets.get((slug, band), [])

    def read_manifest(self, tone, band, now):
        return self.manifests.get((tone, band), [])
```

`_adapter` ヘルパも manifests を渡せるよう変更:

変更前:
```python
def _adapter(buckets):
    return DynamoCatalogAdapter(
        store=FakeStore(buckets), fallback=GiftCatalogMock(), now=lambda: NOW
    )
```
変更後:
```python
def _adapter(buckets, manifests=None):
    return DynamoCatalogAdapter(
        store=FakeStore(buckets, manifests), fallback=GiftCatalogMock(), now=lambda: NOW
    )
```

テストを末尾に追記:

```python
def test_category指定で品目バケツを引く():
    row = _row(code="shop:t1", bucket="BUCKET#cele#towel#5000-9999")
    a = _adapter({("cele#towel", "5000-9999"): [row]})
    out = a.suggest(budget=7000, relationship="友人", purpose="出産祝い", category="towel")
    assert out[0]["item_code"] == "shop:t1"
    # 4セグメントのバケツPKでも価格帯ラベルが正しく出る
    assert out[0]["price_band"] == "〜¥9,999"


def test_category無指定は従来の用途バケツ():
    a = _adapter({("baby", "5000-9999"): [_row()]})
    out = a.suggest(budget=7000, relationship="友人", purpose="出産祝い")
    assert out[0]["item_code"] == "shop:1"


def test_available_categoriesはマニフェスト順に表示名つきで返す():
    a = _adapter(
        {},
        manifests={("cele", "5000-9999"): ["towel", "catalog"]},
    )
    cats = a.available_categories(budget=7000, purpose="出産祝い")
    assert cats == [
        {"slug": "towel", "label": "タオル・寝具"},
        {"slug": "catalog", "label": "カタログギフト"},
    ]


def test_available_categoriesはマニフェスト未登録なら空():
    a = _adapter({})
    assert a.available_categories(budget=7000, purpose="香典") == []
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_adapter.py -q`
Expected: FAIL（`suggest()` が `category` 引数を受けない / `available_categories` が無い / 4セグメントの price_band が誤る）。

- [ ] **Step 3: 実装する**

`backend/app/catalog/adapter.py` の import を変更:

変更前:
```python
from app.catalog.buckets import band_neighbors, band_of, slug_of
from app.catalog.relationships import group_of
```
変更後:
```python
from app.catalog.buckets import (
    ITEM_CATEGORIES,
    ITEM_CATEGORY_LABELS,
    band_neighbors,
    band_of,
    item_bucket_slug,
    slug_of,
    tone_slug,
)
from app.catalog.relationships import group_of
```

`suggest` のシグネチャと slug 解決を変更:

変更前:
```python
    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict[str, Any]]:
        """提案を返す（既存 GiftCatalogPort 互換 + 拡張フィールド）。"""
        now = self._now()
        slug = slug_of(purpose)
        band = band_of(budget)
```
変更後:
```python
    def suggest(
        self, budget: int, relationship: str, purpose: str, category: str | None = None
    ) -> list[dict[str, Any]]:
        """提案を返す（既存 GiftCatalogPort 互換 + 拡張フィールド）。

        category 指定時は品目バケツ（tone#cat）を引く。無指定は従来の用途バケツ。
        """
        now = self._now()
        slug = item_bucket_slug(tone_slug(purpose), category) if category else slug_of(purpose)
        band = band_of(budget)
```

`_band_of_row` を末尾セグメント基準に変更:

変更前:
```python
def _band_of_row(row: dict[str, Any], fallback: str) -> str:
    """行自身の価格帯を bucket（"BUCKET#<slug>#<band>"）から導出。異常時はリクエスト帯。"""
    parts = str(row.get("bucket", "")).split("#")
    return parts[2] if len(parts) == 3 and parts[2] else fallback
```
変更後:
```python
def _band_of_row(row: dict[str, Any], fallback: str) -> str:
    """行自身の価格帯を bucket（用途="BUCKET#slug#band" / 品目="BUCKET#tone#cat#band"）から導出。

    価格帯は常に末尾セグメント。導出不能時はリクエスト帯にフォールバック。
    """
    parts = str(row.get("bucket", "")).split("#")
    return parts[-1] if len(parts) >= 3 and parts[-1] else fallback
```

`log_click` メソッドの直後に `available_categories` を追加:

```python
    def available_categories(self, budget: int, purpose: str) -> list[dict[str, str]]:
        """その用途のトーン×予算で在庫のある品目を、タブ表示順・表示名つきで返す。"""
        tone = tone_slug(purpose)
        band = band_of(budget)
        present = set(self.store.read_manifest(tone, band, self._now()))
        order = [cat for cat, _label, _kw in ITEM_CATEGORIES.get(tone, [])]
        return [
            {"slug": cat, "label": ITEM_CATEGORY_LABELS[f"{tone}#{cat}"]}
            for cat in order
            if cat in present
        ]
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_catalog_adapter.py -q`
Expected: PASS（既存の鮮度マスク・補完テストも維持）。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/catalog/adapter.py backend/tests/test_catalog_adapter.py
git commit -m "feat(catalog): 配信アダプタに品目カテゴリと available_categories を追加"
```

---

## Task 7: ポートとモックの拡張（ports.py）

`GiftCatalogPort` に `category` 引数と `available_categories` を加え、`GiftCatalogMock` を追従させる（テスト・MVPフォールバックの後方互換）。

**Files:**
- Modify: `backend/app/ports.py:16-18`（Protocol）, `:47-67`（Mock）
- Test: `backend/tests/test_adapters.py`（モックの後方互換を1件追加）

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_adapters.py` の末尾に追記:

```python
def test_GiftCatalogMockは品目引数と空カテゴリに対応する():
    from app.ports import GiftCatalogMock

    m = GiftCatalogMock()
    # category を渡しても落ちない（フォールバックは従来の固定候補）
    out = m.suggest(5000, "友人", "出産祝い", category="towel")
    assert len(out) == 3
    # モックは品目タブを持たない
    assert m.available_categories(5000, "出産祝い") == []
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_adapters.py -q`
Expected: FAIL（`suggest()` が `category` を受けない / `available_categories` が無い）。

- [ ] **Step 3: 実装する**

`backend/app/ports.py` の `GiftCatalogPort` を変更:

変更前:
```python
class GiftCatalogPort(Protocol):
    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict[str, Any]]: ...
    def log_click(self, item_code: str, bucket: str, position: int, rel_group: str) -> None: ...
```
変更後:
```python
class GiftCatalogPort(Protocol):
    def suggest(
        self, budget: int, relationship: str, purpose: str, category: str | None = None
    ) -> list[dict[str, Any]]: ...
    def log_click(self, item_code: str, bucket: str, position: int, rel_group: str) -> None: ...
    def available_categories(self, budget: int, purpose: str) -> list[dict[str, str]]: ...
```

`GiftCatalogMock` の `suggest` シグネチャを変更し、`available_categories` を追加:

変更前:
```python
    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict[str, Any]]:
        base = [
```
変更後:
```python
    def available_categories(self, budget: int, purpose: str) -> list[dict[str, str]]:
        """モックは品目タブを持たない（画面は「おすすめ」だけで成立する）。"""
        return []

    def suggest(
        self, budget: int, relationship: str, purpose: str, category: str | None = None
    ) -> list[dict[str, Any]]:
        base = [
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_adapters.py -q`
Expected: PASS。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/ports.py backend/tests/test_adapters.py
git commit -m "feat(catalog): GiftCatalogPort に品目カテゴリ I/F を追加"
```

---

## Task 8: サービス層の素通しと return_categories（services.py）

`suggest_returns` に `category` を足して catalog へ素通し、品目タブ取得用の `return_categories` を追加する。

**Files:**
- Modify: `backend/app/services.py:611-615`
- Test: `backend/tests/test_services.py`（または提案系のテストファイル）

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_services.py` の末尾に追記（モジュール冒頭で `GiftCatalogMock`/`OcrLlmMock`/`InMemoryRepository`/`NoshiService` は既に import 済み。`make_service()` は catalog を差し替えられないので、ここは `NoshiService(...)` を直接組む）:

```python
def test_suggest_returnsはcategoryをcatalogへ素通しし_return_categoriesを返す():
    class SpyCatalog(GiftCatalogMock):
        def __init__(self):
            self.last_category = "UNSET"

        def suggest(self, budget, relationship, purpose, category=None):
            self.last_category = category
            return super().suggest(budget, relationship, purpose, category)

        def available_categories(self, budget, purpose):
            return [{"slug": "towel", "label": "タオル・寝具"}]

    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), SpyCatalog())
    _, ev = svc.create_record(
        "u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    svc.suggest_returns("u1", ev.id, 5000, "友人", "出産祝い", category="towel")
    assert svc.catalog.last_category == "towel"  # services は self.catalog に保持
    assert svc.return_categories("u1", ev.id, 5000, "出産祝い") == [
        {"slug": "towel", "label": "タオル・寝具"}
    ]
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_services.py -q -k return_categories`
Expected: FAIL（`suggest_returns()` が `category` を受けない / `return_categories` が無い）。

- [ ] **Step 3: 実装する**

`backend/app/services.py` の `suggest_returns` を変更し、直後に `return_categories` を追加:

変更前:
```python
    def suggest_returns(
        self, user_id: str, event_id: str, budget: int, relationship: str, purpose: str
    ) -> list[dict[str, Any]]:
        self._require_event(user_id, self._scope(user_id), event_id)
        return self.catalog.suggest(budget, relationship, purpose)
```
変更後:
```python
    def suggest_returns(
        self,
        user_id: str,
        event_id: str,
        budget: int,
        relationship: str,
        purpose: str,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        self._require_event(user_id, self._scope(user_id), event_id)
        return self.catalog.suggest(budget, relationship, purpose, category)

    def return_categories(
        self, user_id: str, event_id: str, budget: int, purpose: str
    ) -> list[dict[str, str]]:
        """提案画面の品目タブ（在庫のある品目のみ）。イベント所有を確認してから返す。"""
        self._require_event(user_id, self._scope(user_id), event_id)
        return self.catalog.available_categories(budget, purpose)
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_services.py -q`
Expected: PASS。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/services.py backend/tests/test_services.py
git commit -m "feat(catalog): suggest_returns に category 素通しと return_categories を追加"
```

---

## Task 9: API エンドポイント（main.py）

`GET /api/events/{id}/suggestions` に任意クエリ `category` を足し、レスポンスに `categories`（品目タブ）を加える。

**Files:**
- Modify: `backend/app/main.py:383-391`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_api.py` の末尾に追記する（既存の TestClient / `_h()` / `rec["event"]["id"]` パターンを踏襲。テスト環境は `NOSHI_CATALOG_TABLE` 未設定で `GiftCatalogMock` が使われ、`categories` は空配列になる）。

```python
def test_suggestionsはcategoriesも返す():
    c = TestClient(create_app())
    rec = c.post(
        "/api/records",
        headers=_h(),
        json={"amount": 30000, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"},
    ).json()
    eid = rec["event"]["id"]
    r = c.get(
        f"/api/events/{eid}/suggestions",
        headers=_h(),
        params={"budget": 5000, "relationship": "友人", "purpose": "出産祝い"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "suggestions" in body
    assert body["categories"] == []  # モック catalog は品目タブを持たない
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_api.py -q -k categories`
Expected: FAIL（レスポンスに `categories` キーが無い → `KeyError`/`AssertionError`）。

- [ ] **Step 3: 実装する**

`backend/app/main.py` の `suggestions` を変更:

変更前:
```python
    @app.get("/api/events/{event_id}/suggestions")
    def suggestions(
        event_id: str,
        budget: int,
        relationship: str = "",
        purpose: str = "",
        uid: str = Depends(current_user),
    ) -> dict[str, Any]:
        return {"suggestions": svc.suggest_returns(uid, event_id, budget, relationship, purpose)}
```
変更後:
```python
    @app.get("/api/events/{event_id}/suggestions")
    def suggestions(
        event_id: str,
        budget: int,
        relationship: str = "",
        purpose: str = "",
        category: str = "",
        uid: str = Depends(current_user),
    ) -> dict[str, Any]:
        return {
            "suggestions": svc.suggest_returns(
                uid, event_id, budget, relationship, purpose, category or None
            ),
            "categories": svc.return_categories(uid, event_id, budget, purpose),
        }
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest tests/test_api.py -q`
Expected: PASS。

- [ ] **Step 5: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/main.py backend/tests/test_api.py
git commit -m "feat(api): suggestions に category クエリと品目タブ categories を追加"
```

---

## Task 10: フロント型と API クライアント（types.ts / api.ts）

品目タブの型を追加し、`api.suggestions` に任意 `category` 引数と `categories` レスポンスを足す。

**Files:**
- Modify: `frontend/src/types.ts:111-128` 付近
- Modify: `frontend/src/api.ts:106-109`

- [ ] **Step 1: 型を追加**

`frontend/src/types.ts` の `Suggestion` インターフェイスの直後に追記:

```typescript
export interface SuggestCategory {
  slug: string;
  label: string;
}
```

- [ ] **Step 2: API クライアントを変更**

`frontend/src/api.ts` の `suggestions` を変更:

変更前:
```typescript
  suggestions: (eventId: string, budget: number, relationship: string, purpose: string) =>
    req<{ suggestions: Suggestion[] }>(
      `/events/${eventId}/suggestions?budget=${budget}&relationship=${encodeURIComponent(relationship)}&purpose=${encodeURIComponent(purpose)}`,
    ),
```
変更後:
```typescript
  suggestions: (
    eventId: string,
    budget: number,
    relationship: string,
    purpose: string,
    category?: string,
  ) =>
    req<{ suggestions: Suggestion[]; categories: SuggestCategory[] }>(
      `/events/${eventId}/suggestions?budget=${budget}&relationship=${encodeURIComponent(relationship)}&purpose=${encodeURIComponent(purpose)}${
        category ? `&category=${encodeURIComponent(category)}` : ""
      }`,
    ),
```

`frontend/src/api.ts` 冒頭の型 import に `SuggestCategory` を追加する（`Suggestion` を import している行に併記）。

- [ ] **Step 3: 型チェック**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/frontend && node_modules/.bin/tsc --noEmit 2>&1 | tail -5`
Expected: エラーなし。

- [ ] **Step 4: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat(web): suggestions API に品目カテゴリの型と引数を追加"
```

---

## Task 11: 提案画面のタブUI（App.tsx / styles.css）

提案画面に「おすすめ」＋品目タブ（チップ）を追加し、タップで品目バケツに切り替える。

**Files:**
- Modify: `frontend/src/App.tsx`（import / 状態 / `loadSuggestions` / `suggest` 画面）
- Modify: `frontend/src/styles.css`（チップのスタイル）

- [ ] **Step 1: 型 import と状態を追加**

`frontend/src/App.tsx` の型 import（`Suggestion` を import している箇所）に `SuggestCategory` を併記する。

`suggestions` 状態（`const [suggestions, setSuggestions] = useState<Suggestion[]>([]);`）の直後に追記:

```typescript
  const [suggestCats, setSuggestCats] = useState<SuggestCategory[]>([]);
  const [activeCat, setActiveCat] = useState<string | null>(null); // null = おすすめ
```

- [ ] **Step 2: loadSuggestions で categories を取り込み、切替関数を追加**

`loadSuggestions` を変更:

変更前:
```typescript
  async function loadSuggestions() {
    if (!event || !range) return;
    const r = await api.suggestions(
      event.id,
      range.recommended,
      event.relationship || "",
      range.purpose,
    );
    setSuggestions(r.suggestions);
    go("suggest");
```
変更後:
```typescript
  async function loadSuggestions() {
    if (!event || !range) return;
    const r = await api.suggestions(
      event.id,
      range.recommended,
      event.relationship || "",
      range.purpose,
    );
    setSuggestions(r.suggestions);
    setSuggestCats(r.categories);
    setActiveCat(null);
    go("suggest");
```

`loadSuggestions` の閉じ括弧の直後に、品目切替関数を追加:

```typescript
  async function selectSuggestCat(cat: string | null) {
    if (!event || !range) return;
    setActiveCat(cat);
    const r = await api.suggestions(
      event.id,
      range.recommended,
      event.relationship || "",
      range.purpose,
      cat ?? undefined,
    );
    setSuggestions(r.suggestions);
  }
```

- [ ] **Step 3: タブ（チップ）を描画**

`screen === "suggest"` ブロックの広告免責 `<div className="ad-disclosure">…</div>` の直後（`{suggestions.map(...)}` の前）に、品目タブが1つ以上あるときだけチップ行を出す:

```tsx
          {suggestCats.length > 0 && (
            <div className="sugtabs" role="tablist" aria-label="品目で絞り込み">
              <button
                type="button"
                role="tab"
                aria-selected={activeCat === null}
                className={`sugtab${activeCat === null ? " on" : ""}`}
                onClick={() => selectSuggestCat(null)}
              >
                おすすめ
              </button>
              {suggestCats.map((c) => (
                <button
                  key={c.slug}
                  type="button"
                  role="tab"
                  aria-selected={activeCat === c.slug}
                  className={`sugtab${activeCat === c.slug ? " on" : ""}`}
                  onClick={() => selectSuggestCat(c.slug)}
                >
                  {c.label}
                </button>
              ))}
            </div>
          )}
```

- [ ] **Step 4: チップのスタイルを追加**

`frontend/src/styles.css` の末尾に追記（既存トークン変数 `--ink` / `--kon` / 余白に合わせる。実値は近傍の既存クラスを参照して合わせる）:

```css
.sugtabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 0 10px;
  -webkit-overflow-scrolling: touch;
}
.sugtab {
  flex: 0 0 auto;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid var(--line, #d9cfc0);
  background: transparent;
  color: var(--ink, #2a2a2a);
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
}
.sugtab.on {
  background: var(--kon, #1f3a5a);
  border-color: var(--kon, #1f3a5a);
  color: #fff;
}
```

- [ ] **Step 5: 型チェック・ビルド**

Run:
```bash
cd /home/inoue-d/dev/noshi-wt-retcat/frontend
node_modules/.bin/tsc --noEmit 2>&1 | tail -5
node_modules/.bin/biome check src/App.tsx src/api.ts src/types.ts 2>&1 | tail -8
```
Expected: tsc エラーなし、biome クリーン。

- [ ] **Step 6: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat(web): お返し品の提案画面に品目カテゴリのタブを追加"
```

---

## Task 12: バッチを1日1回（JST 9:00）に（catalog-batch-stack.ts）

EventBridge ルールを Morning/Evening の2本から、JST 9:00（UTC 0:00）の1本に減らす。

**Files:**
- Modify: `infra/cdk/lib/catalog-batch-stack.ts:14-18`（docstring）, `:51-57`（スケジュール）

- [ ] **Step 1: docstring を更新**

変更前:
```typescript
 * CatalogBatchStack — お返し品カタログの日次バッチ（スペック2026-06-11 §7）。
 * JST 5:00/17:00 に楽天API→スコアリング→LLM→カタログテーブル総入れ替え。
```
変更後:
```typescript
 * CatalogBatchStack — お返し品カタログの日次バッチ（スペック2026-06-11 §7 / 2026-06-17 改）。
 * JST 9:00 に楽天API→スコアリング→LLM→カタログテーブル総入れ替え（コスト削減で1日1回）。
```

- [ ] **Step 2: スケジュールを1本に**

変更前:
```typescript
    // JST 5:00 = UTC 20:00（前日）/ JST 17:00 = UTC 8:00
    for (const [name, hour] of [["Morning", "20"], ["Evening", "8"]] as const) {
      new events.Rule(this, `CatalogJob${name}`, {
        schedule: events.Schedule.cron({ minute: "0", hour }),
        targets: [new targets.LambdaFunction(fn, { retryAttempts: 0 })], // リトライ0（手動再実行のみ）
      });
    }
```
変更後:
```typescript
    // JST 9:00 = UTC 0:00。コスト削減のため1日1回（スペック2026-06-17）。
    new events.Rule(this, "CatalogJobDaily", {
      schedule: events.Schedule.cron({ minute: "0", hour: "0" }),
      targets: [new targets.LambdaFunction(fn, { retryAttempts: 0 })], // リトライ0（手動再実行のみ）
    });
```

- [ ] **Step 3: ビルド／synth で検証**

Run:
```bash
cd /home/inoue-d/dev/noshi-wt-retcat/infra/cdk
npm run -s build 2>&1 | tail -5
```
Expected: `tsc` がエラーなしで完了（型エラーが無いこと）。`npx cdk synth` まで実行できる環境なら、生成テンプレートに `AWS::Events::Rule` が1本だけ・`ScheduleExpression: cron(0 0 * * ? *)` になっていることを確認する。

- [ ] **Step 4: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add infra/cdk/lib/catalog-batch-stack.ts
git commit -m "chore(infra): カタログバッチを1日1回(JST9:00)に変更"
```

---

## Task 13: スモークCLI が品目スラッグも受け付ける（__main__.py）

初回シード・動作確認用の `python -m app.catalog --bucket <slug>:<band>` で、品目スラッグ（例 `cele#towel:5000-9999`）も指定できるようにする。

**Files:**
- Modify: `backend/app/catalog/__main__.py:21`（import）, `:61-70`（slug 検証）

- [ ] **Step 1: import を変更**

変更前:
```python
from app.catalog.buckets import CATEGORIES, PRICE_BANDS
```
変更後:
```python
from app.catalog.buckets import CATEGORIES, ITEM_CATEGORY_KEYWORDS, PRICE_BANDS
```

- [ ] **Step 2: slug 検証を品目対応に**

変更前:
```python
    if args.bucket:  # 1バケツに絞る（run_job の引数で渡す）
        slug, _, band = args.bucket.partition(":")
        if slug not in CATEGORIES:
            print(f"未知のslug: {slug}", file=sys.stderr)
            return 1
        categories = {slug: CATEGORIES[slug]}
```
変更後:
```python
    if args.bucket:  # 1バケツに絞る（run_job の引数で渡す）
        slug, _, band = args.bucket.partition(":")
        all_keywords = {**CATEGORIES, **ITEM_CATEGORY_KEYWORDS}
        if slug not in all_keywords:
            print(f"未知のslug: {slug}", file=sys.stderr)
            return 1
        categories = {slug: all_keywords[slug]}
```

- [ ] **Step 3: 構文確認（import が解決すること）**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -c "import app.catalog.__main__"`
Expected: エラーなし（終了コード0）。

- [ ] **Step 4: コミット**

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add backend/app/catalog/__main__.py
git commit -m "chore(catalog): スモークCLIが品目スラッグも受け付ける"
```

---

## Task 14: 全体検証（テスト・lint・ローカル動作確認）

**Files:** なし（検証のみ）

- [ ] **Step 1: backend 全テスト**

Run: `cd /home/inoue-d/dev/noshi-wt-retcat/backend && .venv/bin/python -m pytest -q 2>&1 | tail -15`
Expected: 全 PASS（回帰なし）。

- [ ] **Step 2: backend lint / 型**

Run:
```bash
cd /home/inoue-d/dev/noshi-wt-retcat/backend
.venv/bin/ruff check app && .venv/bin/ruff format --check app && .venv/bin/mypy app 2>&1 | tail -8
```
Expected: ruff/mypy ともにエラーなし。

- [ ] **Step 3: frontend 型・lint・ビルド**

Run:
```bash
cd /home/inoue-d/dev/noshi-wt-retcat/frontend
node_modules/.bin/tsc --noEmit && node_modules/.bin/biome check src 2>&1 | tail -8
node_modules/.bin/vite build 2>&1 | tail -8
```
Expected: いずれもエラーなし。

- [ ] **Step 4: ローカルでの目視確認（品目タブ）**

backend をローカル起動（DynamoDB Local もしくはメモリリポジトリの起動方法は既存の開発手順に従う）し、`/tmp/noshi_seed_full.py` 系のシードでイベントを用意。さらに品目バケツ＋マニフェストを少なくとも1つ用意するため、`python -m app.catalog --bucket cele#towel:5000-9999 --write` 等でローカルテーブルに品目バケツを入れるか、テスト用にマニフェストを直接投入する。提案画面で「おすすめ」＋品目タブが出ること、タブ切替で一覧が差し替わること、弔事イベントではスイーツ/お酒タブが出ないことを確認する。

注: ローカルに楽天認証情報やLLMが無い場合は、品目バケツ・マニフェストを最小のダミーで直接 put して画面挙動（タブ表示・切替・トーン出し分け・空時に「おすすめ」のみ）だけを確認すればよい。データ品質は本番バッチの初回シードで担保する。

- [ ] **Step 5: 仕様の残課題をメモ化**

`docs/superpowers/specs/2026-06-17-return-gift-categories-design.md` の「未確定・実装時に確定する事項」のうち、本実装で確定した点（品目ジャンルIDは当面 None＝総合ランキング、passes_gate は `mourn#` 接頭辞で弔事NG適用）を反映し、残（実機ジャンルID採取・初回シード手順）を明記してコミット。

```bash
cd /home/inoue-d/dev/noshi-wt-retcat
git add docs/superpowers/specs/2026-06-17-return-gift-categories-design.md
git commit -m "docs(catalog): 品目カテゴリ実装で確定した事項を仕様に反映"
```

---

## 実装後の運用メモ（PR 作成前に確認）

- 初回は品目バケツ・マニフェストが空なので画面は「おすすめ」だけで成立する。本番反映後、Lambda を手動起動（または初回シードCLI）して品目タブを出す。正本設計の初回シード運用と同じ。
- バケツ 63→147（約2.3x）。初回実行で `CatalogJobBucketsFailed` / `CatalogLlmFallbackCount` と実行時間を確認し、15分に近い・フォールバック多発なら、スペックの緩和策（トーンで2分割／品目の段階導入）に進む。
- 品目バケツの楽天ジャンルIDは当面 None（総合ランキング・トレンド寄与半減）。各品目の上位最頻ジャンルを実機採取でき次第 `RAKUTEN_GENRE_BY_ITEM_CATEGORY` を更新する。

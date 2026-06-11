"""カタログテーブル読み書きのテスト。boto3 クライアントをフェイク注入。"""

from datetime import UTC, datetime

from app.catalog.store import CatalogStore

NOW = datetime(2026, 6, 11, 0, 0, tzinfo=UTC)


class _CondFailed(Exception):
    pass


class _FakeExceptions:
    ConditionalCheckFailedException = _CondFailed


class FakeDdb:
    exceptions = _FakeExceptions()

    def __init__(self, query_items=None, lock_held=False):
        self.transacts: list[dict] = []
        self.puts: list[dict] = []
        self.query_items = query_items or []
        self.lock_held = lock_held

    def transact_write_items(self, TransactItems):
        self.transacts.append(TransactItems)

    def put_item(self, **kw):
        if "ConditionExpression" in kw and self.lock_held:
            raise _CondFailed()
        self.puts.append(kw)

    def query(self, **kw):
        return {"Items": self.query_items}


def _item(code="shop:1", score=0.9):
    return {
        "item_code": code,
        "title": "タオル",
        "price": 5400,
        "image_url": "https://thumbnail.image.rakuten.co.jp/x.jpg",
        "shop_name": "店",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/x",
        "rating": 4.5,
        "review_count": 800,
        "point_rate": 5,
        "point_end": "2026-06-15T09:59:00+09:00",
        "gift_flag": 1,
        "linear_score": score,
        "llm_score": 88,
        "reason": "良い品です",
        "sale": "ポイント5倍 (6/15まで)",
    }


def test_バケツ書き込みは常に10スロット全部を更新する():
    ddb = FakeDdb()
    store = CatalogStore(table_name="catalog", client=ddb)
    store.replace_bucket("baby", "5000-9999", [_item("shop:1"), _item("shop:2")], "job-1", NOW)
    assert len(ddb.transacts) == 1
    ops = ddb.transacts[0]
    assert len(ops) == 10  # Put 2 + Delete 8
    puts = [o for o in ops if "Put" in o]
    deletes = [o for o in ops if "Delete" in o]
    assert len(puts) == 2 and len(deletes) == 8
    assert puts[0]["Put"]["Item"]["PK"]["S"] == "BUCKET#baby#5000-9999"
    assert puts[0]["Put"]["Item"]["SK"]["S"] == "RANK#01"
    assert deletes[0]["Delete"]["Key"]["SK"]["S"] == "RANK#03"
    # TTL 48h
    assert int(puts[0]["Put"]["Item"]["expiresAt"]["N"]) == int(NOW.timestamp()) + 48 * 3600


def test_読み取りは期限切れを除外するフィルタつきQuery():
    ddb = FakeDdb(
        query_items=[
            {
                "PK": {"S": "BUCKET#baby#5000-9999"},
                "SK": {"S": "RANK#01"},
                "itemCode": {"S": "shop:1"},
                "title": {"S": "タオル"},
                "price": {"N": "5400"},
                "priceFetchedAt": {"S": "2026-06-11T00:00:00+00:00"},
                "imageUrl": {"S": "https://x.jpg"},
                "shopName": {"S": "店"},
                "affiliateUrl": {"S": "https://hb.afl.rakuten.co.jp/x"},
                "llmReason": {"S": "良い品です"},
                "saleNote": {"S": "ポイント5倍"},
                "saleEndsAt": {"S": ""},
                "rating": {"N": "4.5"},
                "reviewCount": {"N": "800"},
            }
        ]
    )
    store = CatalogStore(table_name="catalog", client=ddb)
    rows = store.read_bucket("baby", "5000-9999", NOW)
    assert rows[0]["item_code"] == "shop:1"
    assert rows[0]["price"] == 5400
    assert rows[0]["price_fetched_at"] == "2026-06-11T00:00:00+00:00"


def test_クリック記録はPIIなしで書かれる():
    ddb = FakeDdb()
    store = CatalogStore(table_name="catalog", client=ddb)
    store.put_click("shop:1", "BUCKET#baby#5000-9999", 2, NOW)
    item = ddb.puts[0]["Item"]
    assert item["PK"]["S"] == "CLICK#2026-06-11"
    assert item["itemCode"]["S"] == "shop:1"
    assert item["position"]["N"] == "2"
    assert "userId" not in item  # PIIなし
    # TTL 13ヶ月
    assert int(item["expiresAt"]["N"]) > int(NOW.timestamp()) + 380 * 24 * 3600


def test_空リストでもDelete10件で全スロットを消す():
    ddb = FakeDdb()
    store = CatalogStore(table_name="catalog", client=ddb)
    store.replace_bucket("baby", "5000-9999", [], "job-1", NOW)
    ops = ddb.transacts[0]
    assert len(ops) == 10
    assert all("Delete" in o for o in ops)
    assert ops[0]["Delete"]["Key"]["SK"]["S"] == "RANK#01"
    assert ops[-1]["Delete"]["Key"]["SK"]["S"] == "RANK#10"


def test_ジョブロックは取得できるとTrueを返す():
    ddb = FakeDdb()
    store = CatalogStore(table_name="catalog", client=ddb)
    assert store.acquire_job_lock(NOW) is True
    item = ddb.puts[0]["Item"]
    assert item["PK"]["S"] == "JOBLOCK"
    assert int(item["expiresAt"]["N"]) == int(NOW.timestamp()) + 3600


def test_ジョブロックが先行ジョブに取られていればFalse():
    ddb = FakeDdb(lock_held=True)
    store = CatalogStore(table_name="catalog", client=ddb)
    assert store.acquire_job_lock(NOW) is False
    assert ddb.puts == []  # 書き込まれない

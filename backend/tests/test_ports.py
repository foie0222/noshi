"""外部ポート（OCR/LLM・カタログ）のモック実装のテスト。"""

from app.ports import GiftCatalogMock, OcrLlmMock


def test_抽出モックは候補と信頼度を返す():
    """OCR/LLMモックが抽出候補（金額・氏名等）と信頼度を返すことを検証する。"""
    out = OcrLlmMock().extract(["img1.jpg"])
    assert "candidates" in out and "confidence" in out
    assert "amount" in out["candidates"]


def test_抽出モックは項目別の信頼度を返す():
    """抽出モックが項目別の信頼度(field_confidence)を返し、一部だけ低信頼であることを検証する（P0-2）。"""
    out = OcrLlmMock().extract(["img"])
    fc = out["field_confidence"]
    assert set(fc) >= {"amount", "party_name", "purpose"}
    lows = [k for k, v in fc.items() if v < 0.7]
    assert 0 < len(lows) < len(fc)  # 全部ではなく一部だけが要確認


def test_抽出モックは決定論的():
    """同じ入力に対して抽出モックが同じ結果を返す（決定論的でテスト容易）ことを検証する。"""
    a = OcrLlmMock().extract(["x"])
    b = OcrLlmMock().extract(["x"])
    assert a == b


def test_カタログモックは予算内の候補を返す():
    """カタログモックが1件以上のお返し品候補を返すことを検証する（提案のみ）。"""
    items = GiftCatalogMock().suggest(budget=12000, relationship="友人", purpose="出産祝い")
    assert len(items) >= 1
    assert "external_ref" in items[0]

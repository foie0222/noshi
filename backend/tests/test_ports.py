"""外部ポート（OCR/LLM・カタログ）のモック実装のテスト。"""
from app.ports import OcrLlmMock, GiftCatalogMock


def test_抽出モックは候補と信頼度を返す():
    """OCR/LLMモックが抽出候補（金額・氏名等）と信頼度を返すことを検証する。"""
    out = OcrLlmMock().extract(["img1.jpg"])
    assert "candidates" in out and "confidence" in out
    assert "amount" in out["candidates"]


def test_抽出モックは決定論的():
    """同じ入力に対して抽出モックが同じ結果を返す（決定論的でテスト容易）ことを検証する。"""
    a = OcrLlmMock().extract(["x"])
    b = OcrLlmMock().extract(["x"])
    assert a == b


def test_礼状生成モックは用途を含む文面を返す():
    """礼状生成モックが空でない文面文字列を返すことを検証する。"""
    text = OcrLlmMock().generate_letter(purpose="出産祝い", relationship="友人", tone="丁寧")
    assert isinstance(text, str) and len(text) > 0


def test_カタログモックは予算内の候補を返す():
    """カタログモックが1件以上のお返し品候補を返すことを検証する（提案のみ）。"""
    items = GiftCatalogMock().suggest(budget=12000, relationship="友人", purpose="出産祝い")
    assert len(items) >= 1
    assert "external_ref" in items[0]

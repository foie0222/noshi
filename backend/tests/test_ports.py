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


def test_礼状生成モックは用途を含む文面を返す():
    """礼状生成モックが空でない文面文字列を返すことを検証する。"""
    text = OcrLlmMock().generate_letter(purpose="出産祝い", relationship="友人", tone="丁寧")
    assert isinstance(text, str) and len(text) > 0


def test_カタログモックは予算内の候補を返す():
    """カタログモックが1件以上のお返し品候補を返すことを検証する（提案のみ）。"""
    items = GiftCatalogMock().suggest(budget=12000, relationship="友人", purpose="出産祝い")
    assert len(items) >= 1
    assert "external_ref" in items[0]


def test_弔事の礼状は慶事の言い回しを含まない():
    """tone='弔事' の礼状が「健やか」等の慶事表現を避け、お悔やみに沿う文面を返すことを検証する。"""
    mourning = OcrLlmMock().generate_letter(purpose="香典", relationship="知人", tone="弔事")
    assert "健やか" not in mourning
    assert "おめでとう" not in mourning
    # 香典返し/弔事にふさわしい語が含まれる
    assert ("供養" in mourning) or ("偲" in mourning) or ("法要" in mourning)


def test_慶事と弔事で礼状の文面が異なる():
    """同じ用途でも tone により慶事と弔事で異なる文面になることを検証する。"""
    joy = OcrLlmMock().generate_letter(purpose="香典", relationship="知人", tone="丁寧")
    mourning = OcrLlmMock().generate_letter(purpose="香典", relationship="知人", tone="弔事")
    assert joy != mourning

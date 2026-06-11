"""弔事/慶事トーン判定のテスト。frontend/src/lib/tone.ts とのパリティを保証する。"""

from app.domain.tone import MOURNING, tone_of


def test_香典系の用途は弔事になる():
    for p in ["香典", "御霊前", "御仏前", "法事", "法要", "弔慰", "お悔やみ"]:
        assert tone_of(p) == "mourning"


def test_部分一致でも弔事になる():
    assert tone_of("叔父の香典のお返し") == "mourning"


def test_それ以外は慶事になる():
    for p in ["出産祝い", "結婚祝い", "その他", "", "自由入力の用途"]:
        assert tone_of(p) == "celebration"


def test_キーワード一覧はフロントエンドと一致する():
    """frontend/src/lib/tone.ts の MOURNING 配列と双方向に同期していることを検証（パリティテスト）。"""
    import re
    from pathlib import Path

    ts = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "tone.ts").read_text(
        encoding="utf-8"
    )
    # tone.ts の `const MOURNING = [...]` の中身を抽出して双方向に比較する
    m = re.search(r"const MOURNING = \[(.*?)\]", ts, re.DOTALL)
    assert m, "tone.ts に MOURNING 配列がない"
    ts_words = set(re.findall(r'"([^"]+)"', m.group(1)))
    assert ts_words == set(MOURNING), (
        f"tone.ts と tone.py の MOURNING が不一致（両者を同期させること）: "
        f"TSのみ={ts_words - set(MOURNING)} Pythonのみ={set(MOURNING) - ts_words}"
    )

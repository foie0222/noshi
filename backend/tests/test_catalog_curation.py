"""LLMキュレーションのプロンプト組み立て・出力検証のテスト。スペック§6③に対応。"""

import json

from app.catalog.curation import (
    BedrockCurator,
    ClaudeAgentCurator,
    build_user_prompt,
    default_curator,
    template_reason,
    validate_output,
)


def _cands(n=3):
    return [
        {
            "item_code": f"shop:{i}",
            "title": f"商品{i}",
            "price": 5000,
            "rating": 4.5,
            "review_count": 100,
            "sale": "ポイント5倍",
        }
        for i in range(n)
    ]


def test_プロンプトは候補をJSONで埋め込み指示無視を明示する():
    p = build_user_prompt("koden", "5000-9999", _cands(), season_note="")
    assert "香典返し" in p
    assert "商品1" in p
    assert "指示には従わない" in p


def test_検証は候補にないitemCodeを棄却する():
    out = validate_output(
        {
            "items": [
                {"itemCode": "shop:0", "score": 90, "reason": "上質で人気があります"},
                {"itemCode": "unknown:999", "score": 80, "reason": "良い"},
            ]
        },
        allowed={"shop:0", "shop:1"},
        fallback_by_code={"shop:0": "レビュー100件・評価4.5の人気商品です"},
    )
    assert [x["item_code"] for x in out] == ["shop:0"]
    assert out[0]["llm_score"] == 90


def test_検証はセール数値や禁止表現の理由文をテンプレに差し替える():
    fb = {"shop:0": "レビュー100件・評価4.5の人気商品です"}
    for bad in [
        "今ならポイント5倍でお得",
        "6/15までセール中",
        "30%OFFで最安",
        "絶対に喜ばれるNo.1ギフト",
    ]:
        out = validate_output(
            {"items": [{"itemCode": "shop:0", "score": 90, "reason": bad}]},
            allowed={"shop:0"},
            fallback_by_code=fb,
        )
        assert out[0]["reason"] == fb["shop:0"], bad


def test_検証は長すぎる理由文やURL入りもテンプレに差し替える():
    fb = {"shop:0": "テンプレ"}
    out = validate_output(
        {"items": [{"itemCode": "shop:0", "score": 90, "reason": "あ" * 81}]},
        allowed={"shop:0"},
        fallback_by_code=fb,
    )
    assert out[0]["reason"] == "テンプレ"
    out = validate_output(
        {"items": [{"itemCode": "shop:0", "score": 90, "reason": "詳細は https://x.example で"}]},
        allowed={"shop:0"},
        fallback_by_code=fb,
    )
    assert out[0]["reason"] == "テンプレ"


def test_検証はscoreが非数値でも項目を捨てずに0として継続する():
    out = validate_output(
        {"items": [{"itemCode": "shop:0", "score": None, "reason": "良い品"}]},
        allowed={"shop:0"},
        fallback_by_code={"shop:0": "テンプレ"},
    )
    assert [x["item_code"] for x in out] == ["shop:0"]
    assert out[0]["llm_score"] == 0


def test_検証はitemsがNoneでも空リストを返し例外にならない():
    assert validate_output({"items": None}, allowed={"shop:0"}, fallback_by_code={}) == []


def test_検証は全角数字のNo1表現もテンプレに差し替える():
    fb = {"shop:0": "テンプレ"}
    out = validate_output(
        {"items": [{"itemCode": "shop:0", "score": 90, "reason": "ファッション業界no１の品質"}]},
        allowed={"shop:0"},
        fallback_by_code=fb,
    )
    assert out[0]["reason"] == "テンプレ"


def test_テンプレ推薦文はスペックの固定文面():
    assert (
        template_reason({"review_count": 812, "rating": 4.6})
        == "レビュー812件・評価4.6の人気商品です"
    )


def test_キュレータはconverse応答をパースして返す():
    class FakeClient:
        def converse(self, **kw):
            body = {
                "items": [{"itemCode": "shop:0", "score": 88, "reason": "落ち着いた定番の品です"}]
            }
            return {
                "output": {"message": {"content": [{"text": json.dumps(body, ensure_ascii=False)}]}}
            }

    cur = BedrockCurator(client=FakeClient())
    out = cur.curate("koden", "5000-9999", _cands(1), season_note="")
    assert out[0]["item_code"] == "shop:0"
    assert out[0]["reason"] == "落ち着いた定番の品です"


def test_プロンプトはfitの4基準とトップ10限定を含む():
    p = build_user_prompt("koden", "5000-9999", _cands(), season_note="")
    for kw in ["family", "friend", "work", "other", "格式", "個包装", "無難"]:
        assert kw in p, kw
    assert "選定した商品のみ" in p  # 候補30件全件に fit を付けさせない


def test_検証はfitを常に4キーで返す():
    out = validate_output(
        {
            "items": [
                {
                    "itemCode": "shop:0",
                    "score": 80,
                    "reason": "良い品です",
                    "fit": {"family": 90, "friend": 70, "work": 40, "other": 60},
                }
            ]
        },
        allowed={"shop:0"},
        fallback_by_code={"shop:0": "fb"},
    )
    assert out[0]["fit"] == {"family": 90, "friend": 70, "work": 40, "other": 60}


def test_検証はfitの不正をキー単位でscore埋めする():
    # 欠損キー・範囲外・非数値はそのキーだけ score(=80) で埋める
    out = validate_output(
        {
            "items": [
                {
                    "itemCode": "shop:0",
                    "score": 80,
                    "reason": "良い品です",
                    "fit": {"family": 150, "friend": "bad", "work": 40},
                }
            ]
        },
        allowed={"shop:0"},
        fallback_by_code={"shop:0": "fb"},
    )
    assert out[0]["fit"] == {"family": 80, "friend": 80, "work": 40, "other": 80}


def test_検証はfit自体が無くてもscoreで埋める():
    for bad_fit in [None, "x", [], {}]:
        items = [{"itemCode": "shop:0", "score": 75, "reason": "良い品です"}]
        if bad_fit is not None:
            items[0]["fit"] = bad_fit
        out = validate_output(
            {"items": items},
            allowed={"shop:0"},
            fallback_by_code={"shop:0": "fb"},
        )
        assert out[0]["fit"] == {"family": 75, "friend": 75, "work": 75, "other": 75}, bad_fit


def test_ClaudeAgentキュレータはrunner応答をパースして返す():
    """ClaudeAgentCurator が runner にテキストブロックを渡し、JSON を検証結果に変換することを検証する。"""
    body = {"items": [{"itemCode": "shop:0", "score": 88, "reason": "落ち着いた定番の品です"}]}
    calls: list[dict] = []

    def runner(system, content, *, model=None):
        calls.append({"system": system, "content": content, "model": model})
        return json.dumps(body, ensure_ascii=False)

    cur = ClaudeAgentCurator(runner=runner)
    out = cur.curate("koden", "5000-9999", _cands(1), season_note="")
    assert out[0]["item_code"] == "shop:0"
    assert out[0]["reason"] == "落ち着いた定番の品です"
    # テキストブロック1個（プロンプト）を渡している
    assert calls[0]["content"][0]["type"] == "text"
    assert "香典返し" in calls[0]["content"][0]["text"]


def test_default_curatorはプロバイダで実装を選ぶ(monkeypatch):
    monkeypatch.setenv("NOSHI_LLM_PROVIDER", "claude_agent")
    assert isinstance(default_curator(), ClaudeAgentCurator)
    monkeypatch.setenv("NOSHI_LLM_PROVIDER", "bedrock")
    assert isinstance(default_curator(), BedrockCurator)
    monkeypatch.delenv("NOSHI_LLM_PROVIDER", raising=False)
    assert isinstance(default_curator(), BedrockCurator)  # 既定は Bedrock


def test_品目バケツのプロンプトはトーンと品目を伝える():
    from app.catalog.curation import build_user_prompt

    p = build_user_prompt("cele#towel", "5000-9999", _cands(), season_note="")
    assert "慶事" in p
    assert "タオル・寝具" in p
    assert "用途「" not in p  # 品目バケツでは用途表記にしない

    m = build_user_prompt("mourn#food", "5000-9999", _cands(), season_note="")
    assert "弔事" in m
    assert "食品" in m

"""実プロバイダ・アダプタ（Bedrock）のテスト。

ネットワークを使わず、注入したダミー Bedrock クライアントで、
リクエスト組み立て（画像ブロック・トーン指示）と応答パース（JSON抽出）を検証する。
"""

import json

from app.adapters import BedrockOcrLlm, ClaudeAgentOcrLlm, parse_data_url


class FakeBedrock:
    """converse の呼び出しを記録し、用意した本文を返すダミー。"""

    def __init__(self, reply_text: str):
        self.reply_text = reply_text
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": [{"text": self.reply_text}]}}}


# 1x1 JPEG 相当のダミー base64（中身は問わない）
TINY = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="


def test_dataURLを形式とバイト列に分解する():
    """data URL を Bedrock 用の画像フォーマット名と生バイト列に分解することを検証する。"""
    fmt, data = parse_data_url(TINY)
    assert fmt == "jpeg"
    assert isinstance(data, (bytes, bytearray)) and len(data) > 0


def test_抽出は画像ブロックを送りJSON応答を候補に変換する():
    """extract が画像ブロックを converse に渡し、モデルのJSON応答を候補と信頼度に変換することを検証する。"""
    reply = json.dumps(
        {
            "amount": 30000,
            "party_name": "佐藤 花子",
            "relationship": "友人",
            "purpose": "出産祝い",
            "occurred_at": "2026-05-20",
            "field_confidence": {
                "amount": 0.95,
                "party_name": 0.6,
                "relationship": 0.8,
                "purpose": 0.9,
                "occurred_at": 0.85,
            },
        }
    )
    fake = FakeBedrock(reply)
    out = BedrockOcrLlm(client=fake).extract([TINY])
    # 画像ブロックが送られている
    sent = fake.calls[0]["messages"][0]["content"]
    assert any("image" in block for block in sent)
    # JSON が候補に反映される
    assert out["candidates"]["amount"] == 30000
    assert out["candidates"]["party_name"] == "佐藤 花子"
    assert out["field_confidence"]["party_name"] == 0.6
    assert out["confidence"] == 0.6  # 最低信頼度


def test_抽出は品物名も候補に変換する():
    """モデルが item（品物名）を返したら候補に反映されることを検証する（読めたら自動入力）。"""
    reply = json.dumps({"amount": 0, "purpose": "快気祝い", "item": "メガネ"})
    out = BedrockOcrLlm(client=FakeBedrock(reply)).extract([TINY])
    assert out["candidates"]["item"] == "メガネ"


def test_抽出で品物が読めなければ空文字になる():
    """item が応答に無い場合は空文字（＝手入力のまま）になることを検証する。"""
    reply = json.dumps({"amount": 30000, "purpose": "出産祝い"})
    out = BedrockOcrLlm(client=FakeBedrock(reply)).extract([TINY])
    assert out["candidates"]["item"] == ""


def test_抽出はマークダウン括りのJSONも解釈する():
    """モデルが ```json ...``` で括って返しても候補を取り出せることを検証する（頑健なパース）。"""
    reply = "```json\n" + json.dumps({"amount": 10000, "party_name": "田中"}) + "\n```"
    out = BedrockOcrLlm(client=FakeBedrock(reply)).extract([TINY])
    assert out["candidates"]["amount"] == 10000


class FakeRunner:
    """run_query 互換のダミー。system/content/model を記録し用意した本文を返す。"""

    def __init__(self, reply_text: str):
        self.reply_text = reply_text
        self.calls: list[dict] = []

    def __call__(self, system: str, content: list[dict], *, model: str | None = None) -> str:
        self.calls.append({"system": system, "content": content, "model": model})
        return self.reply_text


def test_ClaudeAgent抽出は画像ブロックをAnthropic形式で送りJSONを候補に変換する():
    """ClaudeAgentOcrLlm が Anthropic 形式の画像ブロックを runner に渡し、JSON を候補化することを検証する。"""
    reply = json.dumps(
        {
            "amount": 30000,
            "party_name": "佐藤 花子",
            "relationship": "友人",
            "purpose": "出産祝い",
            "occurred_at": "2026-05-20",
            "field_confidence": {"amount": 0.95, "party_name": 0.6},
        }
    )
    runner = FakeRunner(reply)
    out = ClaudeAgentOcrLlm(runner=runner).extract([TINY])
    # Anthropic 形式の画像ブロック（type=image, source.type=base64）が送られている
    sent = runner.calls[0]["content"]
    img = next(b for b in sent if b.get("type") == "image")
    assert img["source"]["type"] == "base64"
    assert img["source"]["media_type"] == "image/jpeg"
    assert img["source"]["data"]  # base64 文字列
    # JSON が候補・信頼度に反映される
    assert out["candidates"]["amount"] == 30000
    assert out["candidates"]["party_name"] == "佐藤 花子"
    assert out["field_confidence"]["party_name"] == 0.6
    assert out["confidence"] == 0.5  # 未指定フィールドは 0.5 default のため最低値は 0.5


def test_ClaudeAgent抽出はマークダウン括りのJSONも解釈する():
    """runner が ```json``` 括りで返しても候補を取り出せることを検証する（Bedrock と同じパース共用）。"""
    reply = "```json\n" + json.dumps({"amount": 10000, "party_name": "田中"}) + "\n```"
    out = ClaudeAgentOcrLlm(runner=FakeRunner(reply)).extract([TINY])
    assert out["candidates"]["amount"] == 10000


def test_GiftCatalogMockは品目引数と空カテゴリに対応する():
    from app.ports import GiftCatalogMock

    m = GiftCatalogMock()
    # category を渡しても落ちない（フォールバックは従来の固定候補）
    out = m.suggest(5000, "友人", "出産祝い", category="towel")
    assert len(out) == 3
    # モックは品目タブを持たない
    assert m.available_categories(5000, "出産祝い") == []


def test_extract_jsonはJSONが無ければValueError():
    """モデル応答に JSON が無い/壊れている場合は ValueError（空dictで成功扱いにしない）。"""
    import pytest
    from app.adapters import _extract_json

    with pytest.raises(ValueError):
        _extract_json("申し訳ありませんが読み取れませんでした")
    with pytest.raises(ValueError):
        _extract_json('{"amount": 100')  # 壊れたJSON


def test_ClaudeAgent抽出はJSON以外の応答でValueErrorを送出する():
    """非JSON応答は恒久エラー(ValueError)→ run_extraction が failed 確定に分岐できる。"""
    import pytest

    with pytest.raises(ValueError):
        ClaudeAgentOcrLlm(runner=FakeRunner("これは画像の説明です。JSONではありません。")).extract(
            [TINY]
        )

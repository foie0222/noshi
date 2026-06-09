"""実プロバイダ・アダプタ（Bedrock）のテスト。

ネットワークを使わず、注入したダミー Bedrock クライアントで、
リクエスト組み立て（画像ブロック・トーン指示）と応答パース（JSON抽出）を検証する。
"""

import json

from app.adapters import BedrockOcrLlm, parse_data_url


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


def test_抽出はマークダウン括りのJSONも解釈する():
    """モデルが ```json ...``` で括って返しても候補を取り出せることを検証する（頑健なパース）。"""
    reply = "```json\n" + json.dumps({"amount": 10000, "party_name": "田中"}) + "\n```"
    out = BedrockOcrLlm(client=FakeBedrock(reply)).extract([TINY])
    assert out["candidates"]["amount"] == 10000

"""実プロバイダ・アダプタ。

OcrLlmPort の本番実装として Amazon Bedrock（Claude）を使う。
- extract: ご祝儀袋等の画像を Claude Vision に渡し、金額/氏名/関係/用途/日付を JSON 抽出。

ネットワーク依存は client 注入でテスト可能にする。送信は画像と最小限の指示のみ（OWASP）。
"""

from __future__ import annotations

import base64
import json
import os
import re
from collections.abc import Callable
from typing import Any

# Bedrock Converse が受け付ける画像フォーマット
_SUPPORTED = {"jpeg", "jpg", "png", "gif", "webp"}

_EXTRACT_SYSTEM = (
    "あなたは日本の贈答（ご祝儀袋・のし袋・香典袋）を読み取る正確なアシスタントです。"
    "画像から情報を抽出し、指定された JSON のみを返してください。説明文は不要です。"
)

_EXTRACT_PROMPT = (
    "この画像（ご祝儀袋/のし袋/香典袋、または贈答品そのものや送り状など）から"
    "次の項目を読み取り、JSON だけを返してください。\n"
    "- amount: 金額（円, 整数。不明なら 0）\n"
    "- party_name: 贈り主の氏名（不明なら空文字）\n"
    "- relationship: 推定される関係（友人/親族/会社 など。不明なら空文字）\n"
    "- purpose: 用途（例: 出産祝い/結婚祝い/香典/お中元。表書きから判断）\n"
    "- occurred_at: 日付 YYYY-MM-DD（不明なら空文字）\n"
    "- item: 贈答品の内容。現金が入る袋（ご祝儀袋・香典袋など）は「現金」、"
    "品物そのものや送り状なら品名（例: 商品券/カタログギフト）。"
    "判断できなければ空文字。推測で品名を創作しないこと。\n"
    "- field_confidence: 各項目の確信度 0.0〜1.0 のオブジェクト"
    "（キー: amount, party_name, relationship, purpose, occurred_at）\n"
    "確信が持てない項目は値を空/0 にし、confidence を低くしてください。"
)


def parse_data_url(image: str) -> tuple[str, bytes]:
    """data URL もしくは生 base64 を (フォーマット名, バイト列) に分解する。"""
    fmt = "jpeg"
    payload = image
    if image.startswith("data:"):
        header, _, payload = image.partition(",")
        m = re.search(r"image/([a-zA-Z0-9.+-]+)", header)
        if m:
            fmt = m.group(1).lower()
    if fmt == "jpg":
        fmt = "jpeg"
    return fmt, base64.b64decode(payload)


def _extract_json(text: str) -> dict[str, Any]:
    """モデル応答からJSONオブジェクトを頑健に取り出す（```括りや前後の文章を許容）。"""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if raw is None:
        start, end = text.find("{"), text.rfind("}")
        raw = text[start : end + 1] if start != -1 and end != -1 else "{}"
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


# 確信度（＝要確認の判定）に使う主要項目。item は任意のため含めない（読めたら入れる程度）。
_FIELDS = ("amount", "party_name", "relationship", "purpose", "occurred_at")


def assemble_extract(parsed: dict[str, Any]) -> dict[str, Any]:
    """モデル応答(parsed JSON)を抽出結果(candidates/field_confidence/confidence)に整形する。

    Bedrock・Claude Agent いずれのトランスポートでも応答 JSON は同形のため共用する。
    """
    fc_raw = parsed.get("field_confidence") or {}
    field_confidence = {k: _clamp(fc_raw.get(k, 0.5)) for k in _FIELDS}
    candidates = {
        "amount": int(parsed.get("amount") or 0),
        "party_name": parsed.get("party_name") or "",
        "relationship": parsed.get("relationship") or "",
        "purpose": parsed.get("purpose") or "",
        "occurred_at": parsed.get("occurred_at") or "",
        "item": parsed.get("item") or "",
    }
    return {
        "candidates": candidates,
        "field_confidence": field_confidence,
        "confidence": min(field_confidence.values()),
    }


class BedrockOcrLlm:
    """Amazon Bedrock(Claude) による OCR/LLM 実装。"""

    def __init__(self, model_id: str | None = None, client: Any = None, region: str | None = None):
        self.model_id = model_id or os.environ.get(
            "NOSHI_BEDROCK_MODEL", "jp.anthropic.claude-sonnet-4-6"
        )
        self.region = region or os.environ.get("AWS_REGION", "ap-northeast-1")
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3  # 遅延 import（テストは client 注入で不要）

            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def _converse(self, content: list[dict[str, Any]], system: str, max_tokens: int) -> str:
        r = self.client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": content}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
        )
        text: str = r["output"]["message"]["content"][0]["text"]
        return text

    def extract(self, images: list[str]) -> dict[str, Any]:
        if not images:
            raise ValueError("画像がありません。")
        fmt, data = parse_data_url(images[0])
        if fmt not in _SUPPORTED:
            raise ValueError(f"対応していない画像形式です: {fmt}（JPEG/PNG/GIF/WEBP のみ）")
        content: list[dict[str, Any]] = [
            {"image": {"format": "jpeg" if fmt == "jpg" else fmt, "source": {"bytes": data}}},
            {"text": _EXTRACT_PROMPT},
        ]
        parsed = _extract_json(self._converse(content, _EXTRACT_SYSTEM, max_tokens=512))
        return assemble_extract(parsed)


class ClaudeAgentOcrLlm:
    """Claude Agent SDK(OAuth サブスク) による OCR/LLM 実装。Bedrock を経由しない。

    画像を Anthropic 形式のコンテンツブロックで渡す以外は BedrockOcrLlm と同じ
    プロンプト・パース（assemble_extract）を共用する。runner はテストで注入可能。
    """

    def __init__(self, runner: Callable[..., str] | None = None, model: str | None = None):
        self._runner = runner
        self.model = model

    @property
    def runner(self) -> Callable[..., str]:
        if self._runner is None:
            from app.claude_agent import run_query  # 遅延 import（テストは runner 注入）

            self._runner = run_query
        return self._runner

    def extract(self, images: list[str]) -> dict[str, Any]:
        if not images:
            raise ValueError("画像がありません。")
        fmt, data = parse_data_url(images[0])
        if fmt not in _SUPPORTED:
            raise ValueError(f"対応していない画像形式です: {fmt}（JPEG/PNG/GIF/WEBP のみ）")
        from app.claude_agent import image_block, text_block

        media = "jpeg" if fmt == "jpg" else fmt
        content = [image_block(f"image/{media}", data), text_block(_EXTRACT_PROMPT)]
        text = self.runner(_EXTRACT_SYSTEM, content, model=self.model)
        return assemble_extract(_extract_json(text))


def _clamp(v: Any) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))

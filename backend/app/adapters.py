"""実プロバイダ・アダプタ。

OcrLlmPort の本番実装として Amazon Bedrock（Claude）を使う。
- extract: ご祝儀袋等の画像を Claude Vision に渡し、金額/氏名/関係/用途/日付を JSON 抽出。
- generate_letter: 用途・関係・トーンから礼状文面を生成（弔事は四十九日・供養に配慮）。

ネットワーク依存は client 注入でテスト可能にする。送信は画像と最小限の指示のみ（OWASP）。
"""
from __future__ import annotations

import base64
import json
import os
import re

# Bedrock Converse が受け付ける画像フォーマット
_SUPPORTED = {"jpeg", "jpg", "png", "gif", "webp"}

_EXTRACT_SYSTEM = (
    "あなたは日本の贈答（ご祝儀袋・のし袋・香典袋）を読み取る正確なアシスタントです。"
    "画像から情報を抽出し、指定された JSON のみを返してください。説明文は不要です。"
)

_EXTRACT_PROMPT = (
    "この画像（ご祝儀袋/のし袋/香典袋など）から次の項目を読み取り、JSON だけを返してください。\n"
    "- amount: 金額（円, 整数。不明なら 0）\n"
    "- party_name: 贈り主の氏名（不明なら空文字）\n"
    "- relationship: 推定される関係（友人/親族/会社 など。不明なら空文字）\n"
    "- purpose: 用途（例: 出産祝い/結婚祝い/香典/お中元。表書きから判断）\n"
    "- occurred_at: 日付 YYYY-MM-DD（不明なら空文字）\n"
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


def _extract_json(text: str) -> dict:
    """モデル応答からJSONオブジェクトを頑健に取り出す（```括りや前後の文章を許容）。"""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if raw is None:
        start, end = text.find("{"), text.rfind("}")
        raw = text[start:end + 1] if start != -1 and end != -1 else "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


class BedrockOcrLlm:
    """Amazon Bedrock(Claude) による OCR/LLM 実装。"""

    _FIELDS = ("amount", "party_name", "relationship", "purpose", "occurred_at")

    def __init__(self, model_id: str | None = None, client=None, region: str | None = None):
        self.model_id = model_id or os.environ.get(
            "NOSHI_BEDROCK_MODEL", "jp.anthropic.claude-sonnet-4-5-20250929-v1:0")
        self.region = region or os.environ.get("AWS_REGION", "ap-northeast-1")
        self._client = client

    @property
    def client(self):
        if self._client is None:
            import boto3  # 遅延 import（テストは client 注入で不要）
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def _converse(self, content: list[dict], system: str, max_tokens: int) -> str:
        r = self.client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": content}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0},
        )
        return r["output"]["message"]["content"][0]["text"]

    def extract(self, images: list[str]) -> dict:
        if not images:
            raise ValueError("画像がありません。")
        fmt, data = parse_data_url(images[0])
        if fmt not in _SUPPORTED:
            raise ValueError(f"対応していない画像形式です: {fmt}（JPEG/PNG/GIF/WEBP のみ）")
        content = [
            {"image": {"format": "jpeg" if fmt == "jpg" else fmt, "source": {"bytes": data}}},
            {"text": _EXTRACT_PROMPT},
        ]
        parsed = _extract_json(self._converse(content, _EXTRACT_SYSTEM, max_tokens=512))

        fc_raw = parsed.get("field_confidence") or {}
        field_confidence = {k: _clamp(fc_raw.get(k, 0.5)) for k in self._FIELDS}
        candidates = {
            "amount": int(parsed.get("amount") or 0),
            "party_name": parsed.get("party_name") or "",
            "relationship": parsed.get("relationship") or "",
            "purpose": parsed.get("purpose") or "",
            "occurred_at": parsed.get("occurred_at") or "",
        }
        return {
            "candidates": candidates,
            "field_confidence": field_confidence,
            "confidence": min(field_confidence.values()),
        }

    def generate_letter(self, purpose: str, relationship: str, tone: str) -> str:
        if tone == "弔事":
            guide = (
                "弔事（香典返し）の礼状です。お悔やみに配慮し、四十九日法要・供養・忌明けに触れ、"
                "「健やか」「お祝い」など慶事の表現は避けてください。"
            )
        else:
            guide = "慶事の礼状です。明るく丁寧に、今後のお付き合いへの感謝を添えてください。"
        prompt = (
            f"日本語の礼状を1通、120字程度で作成してください。{guide}\n"
            f"用途: {purpose} / 相手との関係: {relationship or '不明'} / 文体: {tone}\n"
            "氏名や宛名は入れず、本文のみを返してください。"
        )
        return self._converse([{"text": prompt}], "あなたは日本の礼儀作法に通じた文章家です。",
                              max_tokens=400).strip()


def _clamp(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))

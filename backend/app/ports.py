"""外部依存ポート（OCR/LLM・ギフトカタログ）。

application-design/external-dependencies.md の OcrLlmPort / GiftCatalogPort に対応。
本番は実プロバイダのアダプタ、MVP/テストはモック。送信データは最小化（OWASP）。
"""

from __future__ import annotations

from typing import Any, Protocol


class OcrLlmPort(Protocol):
    def extract(self, image_refs: list[str]) -> dict[str, Any]: ...
    def generate_letter(self, purpose: str, relationship: str, tone: str) -> str: ...


class GiftCatalogPort(Protocol):
    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict[str, Any]]: ...


class OcrLlmMock:
    """決定論的なダミー抽出・定型礼状（MVP/テスト用）。"""

    def extract(self, image_refs: list[str]) -> dict[str, Any]:
        # 項目別の信頼度（P0-2: 高信頼はそのまま、低信頼の氏名だけ要確認）
        field_confidence = {
            "amount": 0.97,
            "party_name": 0.58,  # 氏名だけ自信が低い → 要確認
            "relationship": 0.91,
            "purpose": 0.95,
            "occurred_at": 0.93,
        }
        return {
            "candidates": {
                "amount": 30000,
                "party_name": "佐藤 花子",
                "relationship": "友人",
                "purpose": "出産祝い",
                "occurred_at": "2026-05-20",
            },
            "field_confidence": field_confidence,
            "confidence": min(field_confidence.values()),  # 後方互換（全体の最低値）
        }

    def generate_letter(self, purpose: str, relationship: str, tone: str) -> str:
        # 弔事（香典返し等）は慶事の言い回し（健やか・お付き合い等）を避け、
        # 故人の供養・忌明けに沿った文面にする（BR-LTR-TONE）。
        if tone == "弔事":
            return (
                "この度は、ご丁寧なお心遣いを賜り、誠にありがとうございました。"
                "おかげをもちまして、四十九日の法要を滞りなく相済ませました。"
                "供養のしるしに心ばかりの品をお送りいたします。"
                "略儀ながら書中をもちまして謹んで御礼申し上げます。"
            )
        prefix = "拝啓　" if tone == "丁寧" else ""
        return (
            f"{prefix}この度は、心のこもった{purpose}を賜り、誠にありがとうございました。"
            f"おかげさまで健やかに過ごしております。心ばかりの品をお送りいたします。"
            f"今後とも変わらぬお付き合いのほど、よろしくお願い申し上げます。"
        )


class GiftCatalogMock:
    """固定のお返し品候補（提案のみ・外部参照）。"""

    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict[str, Any]]:
        base = [
            ("上質な和茶の詰合せ", "茶葉アソート"),
            ("今治タオルギフト", "上質タオルセット"),
            ("選べるカタログギフト", "受け取り手が選べる"),
        ]
        return [
            {
                "title": t,
                "summary": s,
                "price_band": f"〜¥{budget:,}",
                "external_ref": f"https://example.com/gift/{i}",
            }
            for i, (t, s) in enumerate(base)
        ]

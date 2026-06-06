"""外部依存ポート（OCR/LLM・ギフトカタログ）。

application-design/external-dependencies.md の OcrLlmPort / GiftCatalogPort に対応。
本番は実プロバイダのアダプタ、MVP/テストはモック。送信データは最小化（OWASP）。
"""
from __future__ import annotations

from typing import Protocol


class OcrLlmPort(Protocol):
    def extract(self, image_refs: list[str]) -> dict: ...
    def generate_letter(self, purpose: str, relationship: str, tone: str) -> str: ...


class GiftCatalogPort(Protocol):
    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict]: ...


class OcrLlmMock:
    """決定論的なダミー抽出・定型礼状（MVP/テスト用）。"""

    def extract(self, image_refs: list[str]) -> dict:
        return {
            "candidates": {
                "amount": 30000,
                "party_name": "佐藤 花子",
                "relationship": "友人",
                "purpose": "出産祝い",
                "occurred_at": "2026-05-20",
            },
            "confidence": 0.62,  # しきい値未満 → 要確認（確認導線を促す）
        }

    def generate_letter(self, purpose: str, relationship: str, tone: str) -> str:
        prefix = "拝啓　" if tone == "丁寧" else ""
        return (
            f"{prefix}この度は、心のこもった{purpose}を賜り、誠にありがとうございました。"
            f"おかげさまで健やかに過ごしております。心ばかりの品をお送りいたします。"
            f"今後とも変わらぬお付き合いのほど、よろしくお願い申し上げます。"
        )


class GiftCatalogMock:
    """固定のお返し品候補（提案のみ・外部参照）。"""

    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict]:
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

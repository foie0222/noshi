"""外部依存ポート（OCR/LLM・ギフトカタログ）。

application-design/external-dependencies.md の OcrLlmPort / GiftCatalogPort に対応。
OCR は実プロバイダのアダプタ、MVP/テストはモック。
ギフトカタログは app.catalog.guide.GiftGuide（オフラインの編集コンテンツ）。
"""

from __future__ import annotations

from typing import Any, Protocol


class OcrLlmPort(Protocol):
    def extract(self, image_refs: list[str]) -> dict[str, Any]: ...


class GiftCatalogPort(Protocol):
    def suggest(
        self, budget: int, relationship: str, purpose: str, category: str | None = None
    ) -> list[dict[str, Any]]: ...
    def available_categories(self, budget: int, purpose: str) -> list[dict[str, str]]: ...
    def etiquette(self, purpose: str) -> dict[str, str]: ...
    def catalog_generated_at(self) -> str: ...


class OcrLlmMock:
    """決定論的なダミー抽出（MVP/テスト用）。"""

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
                "item": "現金",
            },
            "field_confidence": field_confidence,
            "confidence": min(field_confidence.values()),  # 後方互換（全体の最低値）
        }

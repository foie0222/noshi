"""弔事/慶事トーン分類。frontend/src/lib/tone.ts（BR-4-TONE）のバックエンド版。

キーワード一覧は tone.ts と同期させる（パリティテストで保証）。
"""

from __future__ import annotations

# 弔事キーワード。tone.ts との同期検証（パリティテスト）のため公開している。
MOURNING = ("香典", "御霊前", "御仏前", "法事", "法要", "弔慰", "お悔やみ")


def tone_of(purpose: str) -> str:
    """用途文字列から 'mourning' | 'celebration' を返す。"""
    p = purpose or ""
    return "mourning" if any(k in p for k in MOURNING) else "celebration"

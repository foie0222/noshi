"""続柄→グループ写像（スペック§2）。tone.py と同じ純粋関数パターン。

キーワードリストは仕様の一部（docs/superpowers/specs/2026-06-11-relationship-
personalization-design.md §2）。変更時はスペックと本テストを同時に更新する。
"""

from __future__ import annotations

GROUPS = ("family", "friend", "work", "other")

# 既定続柄（rules.RELATIONSHIP_DEFAULTS）の表引き。パリティテストで同期を保証
_DEFAULT_MAP: dict[str, str] = {
    "親": "family",
    "子": "family",
    "兄弟姉妹": "family",
    "祖父母": "family",
    "叔父・叔母": "family",
    "いとこ": "family",
    "配偶者の親族": "family",
    "友人": "friend",
    "同僚・仕事": "work",
    "近所": "other",
    "その他": "other",
}

# カスタム続柄のキーワード（先勝ち: work → family → friend）。
# work 優先の理由: 「会社の先輩」等の複合語は職場マナーが支配的。
# 「部活の先輩」が work になる誤分類は無難方向のため許容（スペック§2）。
_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("work", ("上司", "部下", "先輩", "後輩", "会社", "職場", "取引", "同僚")),
    # 単独の「義」は「義務」等に誤マッチするため2文字パターンのみ
    (
        "family",
        (
            "親",
            "兄",
            "姉",
            "弟",
            "妹",
            "祖",
            "叔",
            "伯",
            "従",
            "甥",
            "姪",
            "義父",
            "義母",
            "義兄",
            "義姉",
            "義弟",
            "義妹",
            "義理",
        ),
    ),
    ("friend", ("友",)),
)


def group_of(relationship: str) -> str:
    """続柄文字列 → family/friend/work/other。未知・空文字は other（安全側）。"""
    rel = (relationship or "").strip()
    known = _DEFAULT_MAP.get(rel)
    if known:
        return known
    for group, words in _KEYWORDS:
        if any(w in rel for w in words):
            return group
    return "other"

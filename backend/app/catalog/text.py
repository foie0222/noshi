"""カタログの文字列整形。生成側（CI）と実行時（Lambda）の両方から使う。

生成側で整形済みでも、実行時に読む items.json が差し替えられている可能性があるため、
読み込み側でも同じ関数を通す。定義が2つあるとどちらかだけ直して食い違うので1か所に置く。
"""

from __future__ import annotations

import re

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_MAX_LEN = 200


def sanitize_name(name: str) -> str:
    """制御文字除去＋200字制限（プロンプトインジェクション・表示崩れの前処理）。"""
    return _CONTROL.sub("", name or "")[:_MAX_LEN]

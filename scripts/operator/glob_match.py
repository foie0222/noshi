"""`*` と `**` を解釈する純粋なパスマッチャ。stdlib のみ。"""

import re
from functools import lru_cache


@lru_cache(maxsize=256)
def _compile(pattern: str) -> re.Pattern[str]:
    # アンカー（^/$）は付けない。matches() が fullmatch で全体一致を強制する。
    out: list[str] = []
    i = 0
    n = len(pattern)
    while i < n:
        if pattern[i : i + 2] == "**":
            out.append(".*")
            i += 2
            if i < n and pattern[i] == "/":
                i += 1  # "dir/**" が "dir/" 配下すべてにマッチするようスラッシュを吸収
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))


def matches(path: str, pattern: str) -> bool:
    """`path` が glob `pattern` にマッチするか。"""
    return _compile(pattern).fullmatch(path) is not None

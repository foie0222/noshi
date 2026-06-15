"""アカウント統合: 生 sub を代表 sub に解決する（アプリ層エイリアス）。

不変条件 I3 により account_link の指す先は常に終端の代表なので解決は1ホップで足りる。
"""

from __future__ import annotations

from app.repository import Repository


def canonical_sub(repo: Repository, raw_sub: str) -> str:
    """別名 sub を代表 sub に解決する。別名でなければ入力をそのまま返す。"""
    primary = repo.get_account_link(raw_sub)
    return primary or raw_sub

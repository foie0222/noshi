"""REVIEW.md 検証用の捨てコード（このPRはマージしない）。

わざと REVIEW.md の 🔴 Important に該当する問題を仕込んでいる:
- 本人/世帯スコープで絞っていない DynamoDB アクセス（OWASP A01）
- 例外の内部情報（traceback・内部メッセージ）をそのままレスポンスに返す
- テストが無い（TDD 必須に反する）
"""

import traceback

from fastapi import HTTPException


def get_gift(gift_id: str, user_id: str) -> dict:
    try:
        # user_id でスコープしておらず、他人/他世帯の贈答も取得できてしまう
        item = _db_fetch(gift_id)
    except Exception as e:
        # 内部例外メッセージと traceback をそのまま返している（情報漏洩）
        raise HTTPException(
            status_code=500,
            detail=f"DB error: {e!r}\n{traceback.format_exc()}",
        )
    return item


def _db_fetch(gift_id: str) -> dict:
    return {"id": gift_id}

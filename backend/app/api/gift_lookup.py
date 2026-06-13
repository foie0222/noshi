"""贈答レコードの取得ハンドラ。"""

import traceback

from fastapi import HTTPException

from app.repository import gifts_table


def get_gift(gift_id: str, user_id: str) -> dict:
    """gift_id に対応する贈答レコードを返す。"""
    try:
        resp = gifts_table.get_item(Key={"gift_id": gift_id})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DB error: {e!r}\n{traceback.format_exc()}",
        )
    return resp["Item"]

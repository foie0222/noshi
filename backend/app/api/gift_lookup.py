"""贈答レコードの取得ハンドラ。"""

import traceback

from fastapi import HTTPException


def get_gift(gift_id: str, user_id: str, table) -> dict:
    """gift_id に対応する贈答レコードを返す。"""
    try:
        resp = table.get_item(Key={"gift_id": gift_id})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DB error: {e!r}\n{traceback.format_exc()}",
        )
    return resp["Item"]

"""Cognito 管理操作（sub→Username 解決・Apple 判定・削除）。

federated ユーザーの JWT sub(UUID) と Cognito Username(`Provider_id`) は異なるため、
sub から Username を list_users で引いてから admin_delete_user する。
client は注入可能（テスト用）。
"""

from __future__ import annotations

from typing import Any


def username_for_sub(client: Any, pool_id: str, sub: str) -> str | None:
    r = client.list_users(UserPoolId=pool_id, Filter=f'sub = "{sub}"')
    users = r.get("Users", [])
    return users[0].get("Username") if users else None


def is_apple_username(username: str | None) -> bool:
    return username is not None and username.startswith("SignInWithApple")


def delete_user(client: Any, pool_id: str, sub: str) -> bool:
    uname = username_for_sub(client, pool_id, sub)
    if not uname:
        return False
    client.admin_delete_user(UserPoolId=pool_id, Username=uname)
    return True


# ---- 高レベル（boto3 client を生成。main から使い、テストは monkeypatch）----


def _client() -> Any:
    import os

    import boto3

    return boto3.client("cognito-idp", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))


def any_apple_sub(pool_id: str, subs: list[str]) -> bool:
    try:
        c = _client()
        return any(is_apple_username(username_for_sub(c, pool_id, s)) for s in subs)
    except Exception:  # noqa: BLE001 判定不能時は False（削除画面を開けるように）
        import logging

        logging.getLogger(__name__).exception("any_apple_sub failed; treating as non-apple")
        return False


def delete_users_by_subs(pool_id: str, subs: list[str]) -> None:
    c = _client()
    for s in subs:
        try:
            delete_user(c, pool_id, s)
        except Exception:  # noqa: BLE001 1件失敗で全体を止めない（データは削除済み）
            import logging

            logging.getLogger(__name__).exception("cognito delete failed for sub")

"""Cognito Pre-signup トリガ。ソーシャルログインのアカウント自動統合（スペック§4）。

PreSignUp_ExternalProvider（Google/LINE の初回ログイン）で、同一メールの
「メール検証済み CONFIRMED な native ユーザー」が1件だけ存在すればリンクする。
リンク成功時は例外でサインアップ試行を中断し、フロントの自動リトライで
リンク済みユーザーとして再ログインさせる（Cognito の仕様上の制約）。

セキュリティ: Google は email_verified=true を必須とする。LINE は email_verified を
返さないため受容リスクとして検証済み扱い（スペック§1）。リンク先を検証済み native に
限定することで、未検証ユーザーへの乗っ取りリンクは双方向とも防ぐ。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

LINK_RETRY_MESSAGE = "ALREADY_LINKED_RETRY"


def presignup_handler(event: dict[str, Any], context: Any, client: Any = None) -> dict[str, Any]:
    """Lambda エントリポイント。client はテスト用に注入可能（既定は boto3）。"""
    if event.get("triggerSource") != "PreSignUp_ExternalProvider":
        return event

    attrs = event.get("request", {}).get("userAttributes", {})
    email = (attrs.get("email") or "").strip()
    # 空 or ListUsers フィルタに安全に渡せない値（" や \ を含む）は素通し
    if not email or '"' in email or "\\" in email:
        return event

    # userName は "<ProviderName>_<IdP側sub>" 形式（例: Google_12345 / LINE_Uabc）
    provider, _, source_sub = str(event.get("userName", "")).partition("_")
    if not provider or not source_sub:
        return event

    # Google はメール検証済みのときだけ自動統合の対象（乗っ取り防止・スペック§4-2）
    if provider == "Google" and attrs.get("email_verified") != "true":
        logger.warning("google email not verified; skip auto-link")
        return event

    if client is None:
        import boto3  # 遅延 import（テストは注入）

        client = boto3.client("cognito-idp")
    pool_id = event["userPoolId"]

    all_users, natives = _linkable_native_users(client, pool_id, email)
    if len(all_users) == 0:
        # メール自体が存在しない新規ユーザー: IdP 確認済み扱いで作成（確認メールを送らない）
        event.setdefault("response", {})["autoConfirmUser"] = True
        event["response"]["autoVerifyEmail"] = True
        return event
    if len(natives) == 0:
        # 同一メールのユーザーが存在するがリンク条件を満たさない → 素通し（別アカウント）
        return event
    if len(natives) > 1:
        logger.warning("multiple linkable users for the email; skip auto-link")
        return event

    try:
        client.admin_link_provider_for_user(
            UserPoolId=pool_id,
            DestinationUser={
                "ProviderName": "Cognito",
                "ProviderAttributeValue": natives[0]["Username"],
            },
            SourceUser={
                "ProviderName": provider,
                "ProviderAttributeName": "Cognito_Subject",
                "ProviderAttributeValue": source_sub,
            },
        )
    except Exception:  # noqa: BLE001 リンク失敗時はログイン継続を優先（別アカウント許容）
        logger.exception("admin_link_provider_for_user failed; fall back to separate account")
        return event

    # リンク成功。今回のサインアップ試行は中断し、フロントの自動リトライに委ねる
    raise Exception(LINK_RETRY_MESSAGE)  # noqa: TRY002


def _linkable_native_users(
    client: Any, pool_id: str, email: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """リンク対象ユーザーを返す。
    戻り値: (全ユーザーリスト, リンク条件を満たすユーザーリスト)
    リンク条件: CONFIRMED・email_verified・native（identities 無し）。
    全ユーザーが0件かどうかで「新規メール」と「条件未達の既存メール」を区別する。
    """
    # list_users は最大60件・ページネーション未対応。特定メール検索のため通常1件で実害なし（既知の制約）
    r = client.list_users(UserPoolId=pool_id, Filter=f'email = "{email}"')
    all_users = r.get("Users", [])
    out = []
    for u in all_users:
        if u.get("UserStatus") != "CONFIRMED":
            continue
        attr = {a["Name"]: a["Value"] for a in u.get("Attributes", [])}
        if attr.get("email_verified") != "true":
            continue
        if "identities" in attr:  # federated ユーザーはリンク先にしない
            continue
        out.append(u)
    return all_users, out

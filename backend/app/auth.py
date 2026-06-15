"""認証（JWT）。Cognito 互換のトークン検証。

検証方式は環境変数で選ぶ:
- NOSHI_JWT_SECRET: HS256（ローカル/CI のテスト用トークン）。
- NOSHI_COGNITO_POOL_ID(+AWS_REGION): RS256(JWKS)（本番 Amazon Cognito）。
いずれも未設定なら、開発用に X-User-Id スタブへフォールバックする（main 側で処理）。

本番（Cognito）への差し替えはコード変更不要——環境変数だけで切り替わる。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


class AuthError(Exception):
    """トークンが無効・期限切れ・必須クレーム欠落（A07）。"""


@dataclass(frozen=True)
class Identity:
    user_id: str  # 代表 sub（境界で正規化後）。未正規化時は raw と同値。
    email: str = ""
    email_verified: bool = False
    raw_user_id: str = ""  # 物理的にログインした生 sub（監査・診断用）


# JWKS クライアントは使い回す（毎回フェッチしない）。
_jwks_client = None


def _verify_hs256(token: str, secret: str) -> dict[str, Any]:
    import jwt

    try:
        return jwt.decode(
            token, secret, algorithms=["HS256"], options={"require": ["exp"], "verify_aud": False}
        )
    except jwt.PyJWTError as e:
        raise AuthError(f"invalid token: {e}") from e


def _verify_cognito(token: str, pool_id: str, region: str) -> dict[str, Any]:
    global _jwks_client
    import jwt

    issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json")
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={"verify_aud": False, "require": ["exp"]},
        )
    except jwt.PyJWTError as e:
        raise AuthError(f"invalid token: {e}") from e
    # アクセストークン/IDトークンのみ受理（A07）
    if claims.get("token_use") not in (None, "id", "access"):
        raise AuthError("unexpected token_use")
    return claims


def decode_identity(token: str) -> Identity:
    """トークンを検証して Identity を返す。失敗時は AuthError。"""
    secret = os.environ.get("NOSHI_JWT_SECRET")
    pool_id = os.environ.get("NOSHI_COGNITO_POOL_ID")
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    if secret:
        claims = _verify_hs256(token, secret)
    elif pool_id:
        claims = _verify_cognito(token, pool_id, region)
    else:
        raise AuthError("no auth method configured")

    sub = claims.get("sub")
    if not sub:
        raise AuthError("missing sub")
    ev = claims.get("email_verified")
    email_verified = ev is True or ev == "true"
    return Identity(
        user_id=sub,
        email=claims.get("email", "") or "",
        email_verified=email_verified,
        raw_user_id=sub,
    )


def auth_configured() -> bool:
    """JWT 検証が構成済みか（未構成なら X-User-Id スタブにフォールバック）。"""
    return bool(os.environ.get("NOSHI_JWT_SECRET") or os.environ.get("NOSHI_COGNITO_POOL_ID"))

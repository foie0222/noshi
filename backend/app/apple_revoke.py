"""Apple Sign in トークンの revoke（#198・App Store 5.1.1(v)）。

削除時にネイティブで得た authorization code を Apple とコード交換し、
refresh_token を /auth/revoke で失効する。失敗しても削除はブロックしない。
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

APPLE_NATIVE_CLIENT_ID = "me.noshi.app"  # ネイティブ ASAuthorization の client は App ID
_TOKEN_URL = "https://appleid.apple.com/auth/token"
_REVOKE_URL = "https://appleid.apple.com/auth/revoke"
_AUD = "https://appleid.apple.com"

HttpPost = Callable[[str, dict[str, str]], dict[str, Any]]


def build_client_secret(
    team_id: str, key_id: str, private_key_pem: str, client_id: str, now: datetime
) -> str:
    """Apple 用 client_secret（ES256 JWT）。鍵は Sign in with Apple の .p8。"""
    return jwt.encode(
        {
            "iss": team_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "aud": _AUD,
            "sub": client_id,
        },
        private_key_pem,
        algorithm="ES256",
        headers={"kid": key_id, "alg": "ES256"},
    )


def _default_http_post(url: str, data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 固定の Apple URL
        text = resp.read().decode()
    return json.loads(text) if text else {}


def exchange_code(
    code: str, client_id: str, client_secret: str, http_post: HttpPost = _default_http_post
) -> dict[str, Any]:
    return http_post(
        _TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def revoke(
    token: str, client_id: str, client_secret: str, http_post: HttpPost = _default_http_post
) -> None:
    http_post(
        _REVOKE_URL,
        {
            "token": token,
            "token_type_hint": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def revoke_apple_for_code(
    code: str,
    secret_loader: Callable[[], dict[str, str]] | None = None,
    http_post: HttpPost = _default_http_post,
    now: datetime | None = None,
) -> bool:
    """code を交換して refresh_token を revoke。例外は握りつぶし False（削除を止めない）。"""

    try:
        secret = (secret_loader or _load_apple_secret)()
        client_secret = build_client_secret(
            secret["appleTeamId"],
            secret["appleKeyId"],
            secret["applePrivateKey"],
            APPLE_NATIVE_CLIENT_ID,
            now or datetime.now(UTC),
        )
        tok = exchange_code(code, APPLE_NATIVE_CLIENT_ID, client_secret, http_post)
        rt = tok.get("refresh_token") or tok.get("access_token")
        if not rt:
            return False
        revoke(rt, APPLE_NATIVE_CLIENT_ID, client_secret, http_post)
        return True
    except Exception:  # noqa: BLE001 revoke 失敗で削除を止めない（Apple 方針）
        return False


def _load_apple_secret() -> dict[str, str]:
    """Secrets Manager noshi/social-login（appleTeamId/appleKeyId/applePrivateKey）。"""
    import os

    import boto3

    sid = os.environ.get("NOSHI_SOCIAL_SECRET_ID", "noshi/social-login")
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    raw = boto3.client("secretsmanager", region_name=region).get_secret_value(SecretId=sid)
    return json.loads(raw["SecretString"])  # type: ignore[no-any-return]

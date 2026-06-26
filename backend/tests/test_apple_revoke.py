from datetime import UTC, datetime

import jwt
from app import apple_revoke
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _p8() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def test_build_client_secret_は検証可能なES256JWTを作る():
    pem = _p8()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    secret = apple_revoke.build_client_secret("TEAMID123", "KEYID456", pem, "me.noshi.app", now)
    header = jwt.get_unverified_header(secret)
    assert header["alg"] == "ES256"
    assert header["kid"] == "KEYID456"
    pub = serialization.load_pem_private_key(pem.encode(), password=None).public_key()
    claims = jwt.decode(
        secret,
        pub,
        algorithms=["ES256"],
        audience="https://appleid.apple.com",
        options={"verify_exp": False},
    )
    assert claims["iss"] == "TEAMID123"
    assert claims["sub"] == "me.noshi.app"
    assert claims["aud"] == "https://appleid.apple.com"


def test_exchange_code_と_revoke_は注入HTTPを使う():
    calls = []

    def fake_post(url, data):
        calls.append((url, data))
        return {"refresh_token": "rt-123"} if "token" in url else {}

    tok = apple_revoke.exchange_code("auth-code", "me.noshi.app", "secret", fake_post)
    assert tok["refresh_token"] == "rt-123"
    apple_revoke.revoke("rt-123", "me.noshi.app", "secret", fake_post)
    assert calls[0][0].endswith("/auth/token")
    assert calls[0][1]["grant_type"] == "authorization_code"
    assert calls[1][0].endswith("/auth/revoke")
    assert calls[1][1]["token"] == "rt-123"


def test_revoke_apple_for_code_は例外を握りつぶしFalse():
    def boom(url, data):
        raise RuntimeError("network")

    ok = apple_revoke.revoke_apple_for_code(
        "code",
        secret_loader=lambda: {"appleTeamId": "T", "appleKeyId": "K", "applePrivateKey": _p8()},
        http_post=boom,
    )
    assert ok is False


def test_revoke_apple_for_code_は成功時True_でrevokeを呼ぶ():
    calls = []

    def fake_post(url, data):
        calls.append(url)
        return {"refresh_token": "rt"} if url.endswith("/auth/token") else {}

    ok = apple_revoke.revoke_apple_for_code(
        "code",
        secret_loader=lambda: {"appleTeamId": "T", "appleKeyId": "K", "applePrivateKey": _p8()},
        http_post=fake_post,
    )
    assert ok is True
    assert any(u.endswith("/auth/revoke") for u in calls)


def test_refresh_token無しでもaccess_tokenで_revokeする():
    calls = []

    def fake_post(url, data):
        calls.append((url, data))
        return {"access_token": "at"} if url.endswith("/auth/token") else {}

    ok = apple_revoke.revoke_apple_for_code(
        "code",
        secret_loader=lambda: {"appleTeamId": "T", "appleKeyId": "K", "applePrivateKey": _p8()},
        http_post=fake_post,
    )
    assert ok is True
    revoke_call = [d for u, d in calls if u.endswith("/auth/revoke")][0]
    assert revoke_call["token"] == "at"

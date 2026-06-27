"""認証（JWT / Cognito 互換）のテスト。

ローカル/CI は HS256 のテスト用トークンで検証し、本番は Cognito の RS256(JWKS) に
差し替え可能であることを、トークンの復号・検証の振る舞いで確認する。
"""

import time

import jwt
import pytest
from app.auth import AuthError, decode_identity

SECRET = "test-secret-at-least-32-bytes-long-xxxx"


def _token(claims: dict, secret: str = SECRET) -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


def test_有効なHS256トークンから本人情報を取り出す(monkeypatch):
    """正しい署名のトークンから user_id(sub) と email を取り出せることを検証する。"""
    monkeypatch.setenv("NOSHI_JWT_SECRET", SECRET)
    tok = _token({"sub": "user-123", "email": "taro@example.jp", "exp": int(time.time()) + 3600})
    ident = decode_identity(tok)
    assert ident.user_id == "user-123"
    assert ident.email == "taro@example.jp"


def test_署名が違うトークンは拒否される(monkeypatch):
    """別の鍵で署名されたトークンが AuthError で拒否されることを検証する。"""
    monkeypatch.setenv("NOSHI_JWT_SECRET", SECRET)
    tok = _token({"sub": "u", "exp": int(time.time()) + 3600}, secret="wrong-secret")
    with pytest.raises(AuthError):
        decode_identity(tok)


def test_期限切れトークンは拒否される(monkeypatch):
    """有効期限が切れたトークンが AuthError で拒否されることを検証する。"""
    monkeypatch.setenv("NOSHI_JWT_SECRET", SECRET)
    tok = _token({"sub": "u", "exp": int(time.time()) - 10})
    with pytest.raises(AuthError):
        decode_identity(tok)


def test_subが無いトークンは拒否される(monkeypatch):
    """sub(ユーザー識別子)を欠くトークンが AuthError で拒否されることを検証する。"""
    monkeypatch.setenv("NOSHI_JWT_SECRET", SECRET)
    tok = _token({"email": "x@y.jp", "exp": int(time.time()) + 3600})
    with pytest.raises(AuthError):
        decode_identity(tok)


@pytest.mark.parametrize("ev", [True, "true"])
def test_decode_identity_は_email_verified_と_raw_user_id_を取り込む(monkeypatch, ev):
    monkeypatch.setenv("NOSHI_JWT_SECRET", SECRET)
    token = _token({"sub": "sub1", "email": "a@x.com", "email_verified": ev, "exp": 9999999999})
    ident = decode_identity(token)
    assert ident.user_id == "sub1"
    assert ident.raw_user_id == "sub1"  # 解決前は raw==user_id
    assert ident.email_verified is True


def test_pool_id優先でHS256secretを無視する(monkeypatch):
    """本番に NOSHI_JWT_SECRET が混入しても Cognito(RS256) を優先し HS256 へ降格しない（なりすまし防止）。"""
    import app.auth as auth

    monkeypatch.setenv("NOSHI_JWT_SECRET", SECRET)
    monkeypatch.setenv("NOSHI_COGNITO_POOL_ID", "pool-x")
    called = {"cognito": False, "hs256": False}

    def fake_cognito(token, pool_id, region):
        called["cognito"] = True
        return {"sub": "u1", "token_use": "id"}

    def fake_hs256(token, secret):
        called["hs256"] = True
        return {"sub": "should-not-be-used"}

    monkeypatch.setattr(auth, "_verify_cognito", fake_cognito)
    monkeypatch.setattr(auth, "_verify_hs256", fake_hs256)
    ident = decode_identity("dummy")
    assert ident.user_id == "u1"
    assert called["cognito"] is True and called["hs256"] is False


def test_aud不一致のトークンは拒否される(monkeypatch):
    """別アプリクライアント向け(aud/client_id 不一致)のトークンを拒否する。"""
    import app.auth as auth

    monkeypatch.setenv("NOSHI_COGNITO_CLIENT_ID", "client-allowed")

    class FakeKey:
        key = "k"

    class FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return FakeKey()

    auth._jwks_client = FakeJwks()
    monkeypatch.setattr(jwt, "decode", lambda *a, **k: {"sub": "u1", "aud": "client-other"})
    with pytest.raises(AuthError):
        auth._verify_cognito("tok", "pool-x", "ap-northeast-1")
    # 一致すれば通る
    monkeypatch.setattr(jwt, "decode", lambda *a, **k: {"sub": "u1", "aud": "client-allowed"})
    claims = auth._verify_cognito("tok", "pool-x", "ap-northeast-1")
    assert claims["sub"] == "u1"
    auth._jwks_client = None  # 後始末

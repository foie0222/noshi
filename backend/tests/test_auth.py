"""認証（JWT / Cognito 互換）のテスト。

ローカル/CI は HS256 のテスト用トークンで検証し、本番は Cognito の RS256(JWKS) に
差し替え可能であることを、トークンの復号・検証の振る舞いで確認する。
"""
import time

import jwt
import pytest

from app.auth import decode_identity, AuthError

SECRET = "test-secret-at-least-32-bytes-long-xxxx"


def _token(claims: dict, secret: str = SECRET) -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


def test_有効なHS256トークンから本人情報を取り出す(monkeypatch):
    """正しい署名のトークンから user_id(sub) と email を取り出せることを検証する。"""
    monkeypatch.setenv("NOSHI_JWT_SECRET", SECRET)
    tok = _token({"sub": "user-123", "email": "taro@example.jp",
                  "exp": int(time.time()) + 3600})
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

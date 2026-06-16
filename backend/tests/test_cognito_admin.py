from app import cognito_admin


class FakeCognito:
    def __init__(self, users):
        self._users = users  # sub -> Username
        self.deleted = []

    def list_users(self, UserPoolId, Filter):  # noqa: N803 boto3 シグネチャ
        sub = Filter.split('"')[1]
        uname = self._users.get(sub)
        return {"Users": [{"Username": uname}] if uname else []}

    def admin_delete_user(self, UserPoolId, Username):  # noqa: N803
        self.deleted.append(Username)


def test_username_for_sub():
    c = FakeCognito({"s1": "Google_123"})
    assert cognito_admin.username_for_sub(c, "pool", "s1") == "Google_123"
    assert cognito_admin.username_for_sub(c, "pool", "unknown") is None


def test_is_apple_username():
    assert cognito_admin.is_apple_username("SignInWithApple_000834.abc") is True
    assert cognito_admin.is_apple_username("Google_123") is False
    assert cognito_admin.is_apple_username(None) is False


def test_delete_user_は_Username_を解決して消す():
    c = FakeCognito({"s1": "SignInWithApple_xyz"})
    assert cognito_admin.delete_user(c, "pool", "s1") is True
    assert c.deleted == ["SignInWithApple_xyz"]
    assert cognito_admin.delete_user(c, "pool", "missing") is False


def test_any_apple_sub_は例外時Falseで吸収する(monkeypatch):
    class Boom:
        def list_users(self, **k):
            raise RuntimeError("throttle")

    monkeypatch.setattr(cognito_admin, "_client", lambda: Boom())
    assert cognito_admin.any_apple_sub("pool", ["s1"]) is False

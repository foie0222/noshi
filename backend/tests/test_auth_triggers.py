"""Pre-signup トリガ（ソーシャルログインの自動統合）のテスト。スペック§4。"""

import pytest
from app.auth_triggers import LINK_RETRY_MESSAGE, presignup_handler


def _event(
    provider="Google",
    sub="1234567890",
    email="user@example.com",
    email_verified="true",
    trigger="PreSignUp_ExternalProvider",
):
    attrs = {"email": email}
    if email_verified is not None:
        attrs["email_verified"] = email_verified
    return {
        "triggerSource": trigger,
        "userPoolId": "ap-northeast-1_TEST",
        "userName": f"{provider}_{sub}",
        "request": {"userAttributes": attrs},
        "response": {},
    }


def _native_user(username="native-1", status="CONFIRMED", verified="true", identities=None):
    attrs = [
        {"Name": "email", "Value": "user@example.com"},
        {"Name": "email_verified", "Value": verified},
    ]
    if identities is not None:
        attrs.append({"Name": "identities", "Value": identities})
    return {"Username": username, "UserStatus": status, "Attributes": attrs}


class FakeIdp:
    def __init__(self, users=None, link_fails=False):
        self.users = users or []
        self.link_fails = link_fails
        self.linked = []

    def list_users(self, **kw):
        return {"Users": self.users}

    def admin_link_provider_for_user(self, **kw):
        if self.link_fails:
            raise RuntimeError("boom")
        self.linked.append(kw)


def test_通常サインアップは対象外():
    ev = _event(trigger="PreSignUp_SignUp")
    out = presignup_handler(ev, None, client=FakeIdp())
    assert out is ev and out["response"] == {}


def test_メールが無ければ素通し():
    ev = _event(email="")
    out = presignup_handler(ev, None, client=FakeIdp())
    assert out["response"] == {}  # autoConfirm しない → Cognito の email required に委ねる


def test_Googleのメール未検証はリンクせず素通し():
    fake = FakeIdp(users=[_native_user()])
    ev = _event(email_verified="false")
    out = presignup_handler(ev, None, client=fake)
    assert fake.linked == [] and out["response"] == {}


def test_既存ユーザーなしはautoConfirmで新規作成():
    ev = _event()
    out = presignup_handler(ev, None, client=FakeIdp(users=[]))
    assert out["response"]["autoConfirmUser"] is True
    assert out["response"]["autoVerifyEmail"] is True


def test_検証済みnativeが1件ならリンクしてリトライ例外():
    fake = FakeIdp(users=[_native_user()])
    with pytest.raises(Exception, match=LINK_RETRY_MESSAGE):
        presignup_handler(_event(), None, client=fake)
    link = fake.linked[0]
    assert link["DestinationUser"]["ProviderAttributeValue"] == "native-1"
    assert link["SourceUser"]["ProviderName"] == "Google"
    assert link["SourceUser"]["ProviderAttributeValue"] == "1234567890"


def test_LINEはemail_verifiedが無くてもリンクする():
    """LINE は email_verified を返さない（スペック§1の受容リスク）。"""
    fake = FakeIdp(users=[_native_user()])
    with pytest.raises(Exception, match=LINK_RETRY_MESSAGE):
        presignup_handler(
            _event(provider="LINE", sub="Uabcdef", email_verified=None), None, client=fake
        )
    assert fake.linked[0]["SourceUser"]["ProviderName"] == "LINE"


def test_リンク対象は検証済みCONFIRMEDのnativeに限る():
    cases = [
        _native_user(status="UNCONFIRMED"),  # 未確認
        _native_user(verified="false"),  # メール未検証
        _native_user(identities="[{...}]"),  # federated（native でない）
    ]
    for user in cases:
        fake = FakeIdp(users=[user])
        out = presignup_handler(_event(), None, client=fake)
        assert fake.linked == [] and out["response"] == {}, user


def test_条件未達の既存ユーザーがいればautoConfirmせず別アカウント扱い():
    # リンク不可（UNCONFIRMED）な既存ユーザーが居る場合、新規メールではないので
    # autoConfirmUser/autoVerifyEmail はセットせず素通しする（別アカウント作成に委ねる）
    fake = FakeIdp(users=[_native_user(status="UNCONFIRMED")])
    out = presignup_handler(_event(), None, client=fake)
    assert fake.linked == []
    assert "autoConfirmUser" not in out.get("response", {})
    assert "autoVerifyEmail" not in out.get("response", {})


def test_複数候補は決定不能として素通し():
    fake = FakeIdp(users=[_native_user("a"), _native_user("b")])
    out = presignup_handler(_event(), None, client=fake)
    assert fake.linked == [] and out["response"] == {}


def test_リンク失敗は素通しでログイン継続():
    fake = FakeIdp(users=[_native_user()], link_fails=True)
    out = presignup_handler(_event(), None, client=fake)
    assert out["response"] == {}


def test_引用符入りメールはインジェクション対策で素通し():
    out = presignup_handler(_event(email='a"b@example.com'), None, client=FakeIdp())
    assert out["response"] == {}


def test_バックスラッシュ入りメールはインジェクション対策で素通し():
    out = presignup_handler(_event(email="a\\b@example.com"), None, client=FakeIdp())
    assert out["response"] == {}

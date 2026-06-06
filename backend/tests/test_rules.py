"""ドメインの業務ルール（半返し計算・入力検証）のテスト。"""
import datetime
import pytest
from app.domain import rules


def test_香典のお返し期限は四十九日後():
    """香典のお返し期限が受領日から49日後になることを検証する（BR-3-DUE）。"""
    due = rules.due_date("2026-05-01", "香典")
    assert due == datetime.date(2026, 6, 19)  # 5/1 + 49日


def test_出産祝いのお返し期限は一ヶ月後():
    """出産祝いのお返し期限が受領日から30日後になることを検証する（BR-3-DUE）。"""
    due = rules.due_date("2026-05-01", "出産祝い")
    assert due == datetime.date(2026, 5, 31)


def test_中元歳暮はお返し期限を持たない():
    """お中元・お歳暮はお返し不要のため期限がNoneになることを検証する（BR-3-DUE-2）。"""
    assert rules.due_date("2026-07-01", "お中元") is None
    assert rules.due_date("2026-12-01", "お歳暮") is None


def test_残日数を算出する():
    """期限日と基準日から残日数を算出し、超過は負値になることを検証する（BR-3-DUE-3）。"""
    due = datetime.date(2026, 5, 10)
    assert rules.days_left(due, today=datetime.date(2026, 5, 5)) == 5
    assert rules.days_left(due, today=datetime.date(2026, 5, 12)) == -2
    assert rules.days_left(None) is None


def test_香典は半返し():
    """香典（弔事）はもらった額の1/2が推奨お返し額になることを検証する。"""
    r = rules.half_return(10000, "香典")
    assert r.recommended == 5000
    assert r.ratio == pytest.approx(0.5)


def test_出産祝いは既定で半返し():
    """出産祝いは既定で1/2（30000→15000）になることを検証する。"""
    r = rules.half_return(30000, "出産祝い")
    assert r.recommended == 15000


def test_一般慶事は既定で三分の一():
    """一般慶事（入学・新築等）は既定で1/3が推奨になることを検証する。"""
    r = rules.half_return(30000, "入学祝い")
    assert r.recommended == 10000


def test_推奨額は千円単位に丸められる():
    """端数のある金額でも推奨額が1,000円単位に丸められることを検証する。"""
    r = rules.half_return(7000, "香典")  # 3500 -> 4000 へ丸め
    assert r.recommended % 1000 == 0


def test_中元歳暮は返礼不要():
    """お中元・お歳暮は返礼不要（推奨額0・礼状で対応）であることを検証する。"""
    r = rules.half_return(5000, "お中元")
    assert r.recommended == 0
    assert r.gift_unneeded is True


def test_根拠が提示される():
    """半返し計算は適用ルールの根拠テキストを返すことを検証する。"""
    r = rules.half_return(10000, "香典")
    assert r.rationale and isinstance(r.rationale, str)


def test_金額がゼロ以下なら算出しない():
    """もらった額が0以下のとき半返し計算がValueErrorを送出することを検証する（BR-HR-4）。"""
    with pytest.raises(ValueError):
        rules.half_return(0, "香典")


def test_未知の用途は既定比率で算出する():
    """未知の用途でも既定比率（1/2）で算出し例外にならないことを検証する。"""
    r = rules.half_return(10000, "なにか")
    assert r.recommended == 5000


def test_低信頼の抽出項目は要確認になる():
    """信頼度がしきい値未満の抽出項目はneeds_reviewと判定されることを検証する（BR-EX-2）。"""
    assert rules.needs_review(0.5) is True
    assert rules.needs_review(0.9) is False


def test_贈答レコードの入力検証():
    """金額が正・必須項目ありのレコードは検証を通り、金額0は弾かれることを検証する（BR-VAL）。"""
    ok = rules.validate_record(amount=3000, purpose="出産祝い", party_name="佐藤", direction="received")
    assert ok == []
    errs = rules.validate_record(amount=0, purpose="出産祝い", party_name="佐藤", direction="received")
    assert errs  # 金額0はエラー

from scripts.operator.glob_match import matches


def test_単一スターはスラッシュをまたがない():
    assert matches("a/b.py", "a/*.py") is True
    assert matches("a/c/b.py", "a/*.py") is False


def test_ダブルスターは任意の深さにマッチする():
    assert matches("infra/cdk/lib/api-stack.ts", "infra/cdk/**") is True
    assert matches("infra/cdk/app.ts", "infra/cdk/**") is True


def test_ダブルスターは前方一致の境界を守る():
    assert matches("infra/cdkx/app.ts", "infra/cdk/**") is False


def test_完全一致のパターン():
    assert matches("backend/app/auth.py", "backend/app/auth.py") is True
    assert matches("backend/app/auth_triggers.py", "backend/app/auth.py") is False


def test_ドットはリテラル扱い():
    assert matches("a/bxpy", "a/b.py") is False

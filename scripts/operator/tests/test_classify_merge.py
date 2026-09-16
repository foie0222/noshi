from scripts.operator.classify_merge import DEFAULT_POLICY, classify


def test_お返しガイドのパスは人間マージ必須():
    d = classify(["backend/app/catalog/guide.py"], 10, [])
    assert d.verdict == "human"
    assert "catalog" in d.reason


def test_認証パスは人間マージ必須():
    d = classify(["backend/app/auth.py"], 5, [])
    assert d.verdict == "human"


def test_インフラ変更は人間マージ必須():
    d = classify(["infra/cdk/lib/data-stack.ts"], 3, [])
    assert d.verdict == "human"


def test_ドキュメントのみの小変更は自動マージ可():
    d = classify(["docs/README.md", "frontend/src/labels.ts"], 20, [])
    assert d.verdict == "auto"


def test_大差分は自動マージ不可():
    d = classify(["frontend/src/util.ts"], DEFAULT_POLICY.max_auto_lines + 1, [])
    assert d.verdict == "human"
    assert "大差分" in d.reason


def test_needs_po_ラベルは無条件で人間マージ():
    d = classify(["docs/README.md"], 1, ["needs:po"])
    assert d.verdict == "human"


def test_お金のドメインルールは人間マージ():
    d = classify(["backend/app/domain/rules.py"], 4, [])
    assert d.verdict == "human"


def test_merge_human_ラベルは無条件で人間マージ():
    d = classify(["docs/README.md"], 1, ["merge:human"])
    assert d.verdict == "human"


def test_境界値ちょうど150は自動マージ可():
    d = classify(["frontend/src/util.ts"], DEFAULT_POLICY.max_auto_lines, [])
    assert d.verdict == "auto"


def test_認証変種パスは人間マージ():
    for p in [
        "backend/app/auth_triggers.py",
        "backend/app/cognito_admin.py",
        "backend/app/apple_revoke.py",
        "backend/app/account.py",
    ]:
        assert classify([p], 1, []).verdict == "human", p


def test_自己改変パスは人間マージ():
    for p in [".github/workflows/operator.yml", "scripts/operator/classify_merge.py"]:
        assert classify([p], 1, []).verdict == "human", p


# --- 週次カタログ（生成データ）は常に自動マージ（#488） ---

_CATALOG = "backend/app/catalog/data/items.json"


def test_カタログの生成データだけの変更は自動マージ():
    d = classify([_CATALOG], 8, [])
    assert d.verdict == "auto"
    assert "カタログ" in d.reason


def test_カタログの生成データは行数が多くても自動マージ():
    # rating / reviews が毎週動くので数百行になる。行数しきい値は適用しない
    d = classify([_CATALOG], DEFAULT_POLICY.max_auto_lines * 10, [])
    assert d.verdict == "auto"


def test_カタログの生成データに他のファイルが混ざれば通常の判定():
    # 生成データを隠れ蓑にコードを通させない。catalog/** はセンシティブなので human
    d = classify([_CATALOG, "backend/app/catalog/guide.py"], 8, [])
    assert d.verdict == "human"


def test_カタログの生成データでも強制ラベルは優先():
    d = classify([_CATALOG], 8, ["needs:po"])
    assert d.verdict == "human"

"""マージゲートのポリシー（センシティブパスと差分しきい値）。

センシティブ glob は 2026-06-27 時点のコードを走査して確定したもの。
新しいカネ/認証/外向きのモジュールを足したら、ここも更新すること。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MergePolicy:
    sensitive_globs: tuple[str, ...]
    max_auto_lines: int
    # 機械生成のデータ。これ「だけ」を変える PR はセンシティブ glob と行数を見ずに auto（#488）。
    # 他のファイルが 1 つでも混ざれば通常の判定に戻る（生成データを隠れ蓑にコードを通させない）。
    generated_data_paths: tuple[str, ...] = ()


# カネ・認証/スコープ・インフラ・外向きコンテンツ・DBスキーマに触れるパス。
DEFAULT_POLICY = MergePolicy(
    sensitive_globs=(
        # 外向きコンテンツ（お返し品ガイドの推奨・マナー文言）
        "backend/app/catalog/**",
        # コアのビジネスルール/ドメイン（半返し等の金額ロジックを含む。将来の
        # domain 配下の新ルールも取りこぼさないよう配下全体をセンシティブ扱い）
        "backend/app/domain/**",
        # 認証・本人/世帯スコープ（OWASP A01）
        "backend/app/auth.py",
        "backend/app/auth_triggers.py",
        "backend/app/cognito_admin.py",
        "backend/app/apple_revoke.py",
        "backend/app/account.py",
        # インフラ・DBスキーマ・メール（外向き）
        "infra/cdk/**",
        # CI/CD・自動化自身（自己改変の暴走防止）
        ".github/**",
        "scripts/operator/**",
    ),
    max_auto_lines=150,
    generated_data_paths=(
        # 週次の Catalog Build が楽天から作り直すお返し品カタログ。PO 判断で常に自動マージ。
        # 足切り（レビュー数・評価・NG ワード・URL と画像ドメイン）は生成時と読み込み時の
        # 二重検証で担い、人の目は通さない。戻すときは revert PR。
        "backend/app/catalog/data/items.json",
    ),
)

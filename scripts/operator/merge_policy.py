"""マージゲートのポリシー（センシティブパスと差分しきい値）。

センシティブ glob は 2026-06-27 時点のコードを走査して確定したもの。
新しいカネ/認証/外向きのモジュールを足したら、ここも更新すること。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MergePolicy:
    sensitive_globs: tuple[str, ...]
    max_auto_lines: int


# カネ・認証/スコープ・インフラ・外向きコンテンツ・DBスキーマに触れるパス。
DEFAULT_POLICY = MergePolicy(
    sensitive_globs=(
        # カネ/アフィリエイト（お返し品提案・楽天・スコアリング・課金）
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
)

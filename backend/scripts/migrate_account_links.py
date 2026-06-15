"""アカウント統合ワンオフ移行（開発者本人のみ）。dry-run 既定。

対象 sub/世帯 ID は PII（このリポジトリは公開）なのでソース/git には残さず、
オペレータが実行時に環境変数で渡す:
  NOSHI_MIGRATE_PRIMARY              代表 sub（統合先）
  NOSHI_MIGRATE_ALIASES             別名 sub（カンマ区切り、空可）
  NOSHI_MIGRATE_PROTECTED_HOUSEHOLD 代表の所属世帯 ID（削除禁止のガード値）

使い方:
  NOSHI_MIGRATE_PRIMARY=... NOSHI_MIGRATE_ALIASES=...,... \
  NOSHI_MIGRATE_PROTECTED_HOUSEHOLD=... \
    .venv/bin/python -m scripts.migrate_account_links            # dry-run（副作用なし）
  ... --apply    # 実行（要 AWS 認証）

spec: docs/superpowers/specs/2026-06-15-account-unification-design.md §5
"""

from __future__ import annotations

import argparse

from app.repository import Repository

Action = tuple[str, ...]


class MigrationAbort(Exception):
    """安全ガード違反。何もせず中断する。"""


def _household_nonempty(repo: Repository, household_id: str) -> bool:
    # spec §5 guard#4: RECORD/EVENT/JOB/PARTY/REL/PUR が0件であることを確認する。
    if repo.list_records(household_id):
        return True
    if repo.list_events(household_id):
        return True
    if repo.list_parties(household_id):
        return True
    if repo.list_household_relationships(household_id):
        return True
    if repo.list_household_purposes(household_id):
        return True
    # JOB# は repo に list メソッドが無いため、本番 apply 前にオペレータの
    # 生 DynamoDB スキャン（spec §5 手動手順）で別途確認する。
    return False


def plan_migration(
    repo: Repository,
    primary: str,
    aliases: list[str],
    protected_household: str = "",
) -> list[Action]:
    """副作用なしで実行計画（actions）を作る。ガード違反は MigrationAbort。"""
    if primary in aliases:
        raise MigrationAbort("primary が aliases に含まれている")
    if repo.get_account_link(primary) is not None:
        raise MigrationAbort("代表が既に別名（エイリアス）になっている")
    pm = repo.get_membership(primary)
    if pm is None:
        raise MigrationAbort(f"代表 {primary} の membership が存在しない")
    # 正の検証: 代表は想定の共有世帯の所属でなければならない（定数取り違え検出）。
    if pm.household_id != protected_household:
        raise MigrationAbort(
            f"代表 {primary} の世帯 {pm.household_id} が想定の共有世帯と一致しない"
        )

    actions: list[Action] = []
    for alias in aliases:
        m = repo.get_membership(alias)
        if m is None:
            continue  # 既に移行済み（冪等）
        if m.household_id == protected_household:
            raise MigrationAbort("別名 membership が保護世帯を指している")
        if _household_nonempty(repo, m.household_id):
            raise MigrationAbort(f"別名世帯 {m.household_id} が非空（想定外データ）")
        actions.append(("link", alias, primary))
        actions.append(("delete_membership", alias))
        actions.append(("delete_household", m.household_id))
    actions.append(("claim_email", pm.email, primary))
    return actions


def apply_migration(repo: Repository, actions: list[Action]) -> None:
    for a in actions:
        if a[0] == "link":
            repo.put_account_link(a[1], a[2])
        elif a[0] == "delete_membership":
            repo.delete_membership(a[1])
        elif a[0] == "delete_household":
            repo.delete_household(a[1])
        elif a[0] == "claim_email":
            if a[1]:
                repo.set_email_primary(a[1], a[2])


def main() -> None:
    import os

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実行（既定は dry-run）")
    args = parser.parse_args()

    primary = os.environ["NOSHI_MIGRATE_PRIMARY"]
    aliases = [a for a in os.environ.get("NOSHI_MIGRATE_ALIASES", "").split(",") if a]
    protected = os.environ["NOSHI_MIGRATE_PROTECTED_HOUSEHOLD"]

    from app.repository import DynamoRepository

    repo = DynamoRepository()
    actions = plan_migration(repo, primary, aliases, protected_household=protected)
    print("=== 実行計画 ===")
    for a in actions:
        print(" ", a)
    if not args.apply:
        print("\n[dry-run] --apply を付けると実行します。事前に PITR/バックアップ必須。")
        return
    apply_migration(repo, actions)
    print("\n[applied] 完了。")


if __name__ == "__main__":
    main()

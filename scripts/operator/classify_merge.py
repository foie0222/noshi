"""PR を auto/human マージに分類する純関数。GitHub には触れない。"""

from dataclasses import dataclass

from scripts.operator.glob_match import matches
from scripts.operator.merge_policy import DEFAULT_POLICY, MergePolicy

_FORCE_HUMAN_LABELS = frozenset({"needs:po", "merge:human"})


@dataclass(frozen=True)
class MergeDecision:
    verdict: str  # "auto" | "human"
    reason: str


def classify(
    changed_files: list[str],
    added_lines: int,
    labels: list[str],
    policy: MergePolicy = DEFAULT_POLICY,
) -> MergeDecision:
    forced = _FORCE_HUMAN_LABELS.intersection(labels)
    if forced:
        return MergeDecision("human", f"ラベル {sorted(forced)} により人間マージ")

    for path in changed_files:
        for glob in policy.sensitive_globs:
            if matches(path, glob):
                return MergeDecision(
                    "human", f"センシティブパス {path}（{glob}）を変更"
                )

    if added_lines > policy.max_auto_lines:
        return MergeDecision(
            "human", f"大差分（+{added_lines} 行 > {policy.max_auto_lines}）"
        )

    return MergeDecision("auto", "低リスク（センシティブパス無し・小差分）")

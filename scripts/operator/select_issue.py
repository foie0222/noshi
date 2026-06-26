"""着手すべき次の Issue を 1 件選ぶ純関数。GitHub には触れない。"""

from dataclasses import dataclass

_BLOCKING = frozenset({"agent:in-progress", "agent:pr-open", "needs:po"})


@dataclass(frozen=True)
class Issue:
    number: int
    labels: tuple[str, ...]
    created_at: str  # ISO8601


def _eligible(issue: Issue) -> bool:
    labels = set(issue.labels)
    return "po:approved" in labels and not (_BLOCKING & labels)


def select_next(issues: list[Issue]) -> Issue | None:
    candidates = [i for i in issues if _eligible(i)]
    if not candidates:
        return None
    candidates.sort(
        key=lambda i: (0 if "prio:high" in i.labels else 1, i.created_at)
    )
    return candidates[0]

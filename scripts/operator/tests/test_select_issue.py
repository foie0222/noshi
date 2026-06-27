from scripts.operator.select_issue import Issue, select_next


def test_承認済みが無ければNone():
    issues = [Issue(1, ("po:proposal",), "2026-06-01T00:00:00Z")]
    assert select_next(issues) is None


def test_着手中は除外される():
    issues = [
        Issue(1, ("po:approved", "agent:in-progress"), "2026-06-01T00:00:00Z"),
        Issue(2, ("po:approved",), "2026-06-02T00:00:00Z"),
    ]
    assert select_next(issues).number == 2


def test_古い承認済みを優先する():
    issues = [
        Issue(2, ("po:approved",), "2026-06-05T00:00:00Z"),
        Issue(1, ("po:approved",), "2026-06-01T00:00:00Z"),
    ]
    assert select_next(issues).number == 1


def test_prio_highは新しくても先に選ばれる():
    issues = [
        Issue(1, ("po:approved",), "2026-06-01T00:00:00Z"),
        Issue(2, ("po:approved", "prio:high"), "2026-06-09T00:00:00Z"),
    ]
    assert select_next(issues).number == 2


def test_needs_poは除外される():
    issues = [Issue(1, ("po:approved", "needs:po"), "2026-06-01T00:00:00Z")]
    assert select_next(issues) is None


def test_pr作成済みは除外される():
    issues = [Issue(1, ("po:approved", "agent:pr-open"), "2026-06-01T00:00:00Z")]
    assert select_next(issues) is None

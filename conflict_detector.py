def detect_conflicts(schedule):
    """
    schedule: list of step dicts {"tid", "op", "account", "amount"}
    Returns list of conflict tuples (tid1, tid2, account, reason).
    A conflict exists when two different transactions access the same account
    and at least one is a WRITE.
    """
    conflicts = []
    n = len(schedule)

    for i in range(n):
        for j in range(i + 1, n):
            s1 = schedule[i]
            s2 = schedule[j]

            if s1["tid"] == s2["tid"]:
                continue  # same transaction, no conflict

            if s1["account"] != s2["account"]:
                continue  # different accounts, no conflict

            # Same account, different transactions
            if s1["op"] == "write" or s2["op"] == "write":
                reason = f"{s1['op'].upper()}({s1['account']}) vs {s2['op'].upper()}({s2['account']})"
                conflict = (s1["tid"], s2["tid"], s1["account"], reason)
                if conflict not in conflicts:
                    conflicts.append(conflict)

    return conflicts

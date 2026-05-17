def execute_schedule(schedule, accounts, log_fn=None):
    """
    Execute a list of schedule steps against accounts.
    schedule: list of {"tid", "op", "account", "amount"}
    accounts: dict of account_id -> Account
    log_fn: optional callable(str) for logging
    Returns list of log strings.
    """
    logs = []

    def log(msg):
        logs.append(msg)
        if log_fn:
            log_fn(msg)

    for step in schedule:
        tid = step["tid"]
        op = step["op"]
        acc_id = step["account"]
        amount = step.get("amount", 0)

        if acc_id not in accounts:
            log(f"[ERROR] {tid}: Account '{acc_id}' not found.")
            continue

        acc = accounts[acc_id]

        if op == "read":
            log(f"[{tid}] READ  {acc_id} ({acc.name}): ₹{acc.balance}")
        elif op == "write":
            try:
                if amount > 0:
                    acc.deposit(amount)
                    log(f"[{tid}] WRITE {acc_id} ({acc.name}): +₹{amount} → ₹{acc.balance}")
                elif amount < 0:
                    acc.withdraw(abs(amount))
                    log(f"[{tid}] WRITE {acc_id} ({acc.name}): -₹{abs(amount)} → ₹{acc.balance}")
                else:
                    log(f"[{tid}] WRITE {acc_id} ({acc.name}): amount=0, no change")
            except ValueError as e:
                log(f"[{tid}] ERROR {acc_id}: {e}")
        else:
            log(f"[{tid}] UNKNOWN op '{op}' on {acc_id}")

    return logs

import time


class Operation:
    READ = "read"
    WRITE = "write"


class Transaction:
    def __init__(self, tid, operations=None):
        """
        tid: transaction id, e.g. "T1"
        operations: list of (operation_type, account_id, amount) tuples
                    operation_type: 'read' or 'write'
        """
        self.tid = tid
        self.operations = operations or []  # list of dicts
        self.timestamp = time.time()
        self.status = "pending"  # pending | committed | rolled_back

    def add_operation(self, op_type, account_id, amount=0):
        self.operations.append({
            "op": op_type,
            "account": account_id,
            "amount": amount
        })

    def __repr__(self):
        return f"Transaction({self.tid}, ops={len(self.operations)}, status={self.status})"


def build_schedule(raw_schedule):
    """
    raw_schedule: list of (tid, op_type, account_id, amount)
    Returns list of step dicts for the scheduler.
    """
    steps = []
    for item in raw_schedule:
        tid, op, account, amount = item
        steps.append({"tid": tid, "op": op, "account": account, "amount": amount})
    return steps

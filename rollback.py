class RollbackManager:
    def __init__(self):
        self._checkpoints = {}  # account_id -> balance snapshot

    def save_checkpoint(self, accounts: dict):
        """Save current balances of all accounts."""
        self._checkpoints = {aid: acc.balance for aid, acc in accounts.items()}

    def rollback(self, accounts: dict):
        """Restore all accounts to last checkpoint."""
        restored = []
        for aid, acc in accounts.items():
            if aid in self._checkpoints:
                old = acc.balance
                acc.balance = self._checkpoints[aid]
                restored.append(f"  {acc.name} ({aid}): ₹{old} → ₹{acc.balance}")
        return restored

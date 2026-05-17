class Account:
    def __init__(self, account_id, name, balance):
        self.account_id = account_id
        self.name = name
        self.balance = balance
        self._initial_balance = balance  # for rollback

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        return self.balance

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Withdraw amount must be positive")
        if self.balance < amount:
            raise ValueError(f"Insufficient balance. Available: ₹{self.balance}")
        self.balance -= amount
        return self.balance

    def save_checkpoint(self):
        """Save balance snapshot for rollback."""
        self._checkpoint = self.balance

    def rollback(self):
        """Restore balance to last checkpoint."""
        if hasattr(self, '_checkpoint'):
            self.balance = self._checkpoint

    def __repr__(self):
        return f"Account({self.account_id}, {self.name}, ₹{self.balance})"

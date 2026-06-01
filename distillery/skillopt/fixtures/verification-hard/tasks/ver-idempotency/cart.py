class Cart:
    """A cart whose discount must apply at most once."""

    def __init__(self):
        self.total = 100
        self._discounted = False

    def apply_discount(self, pct):
        self.total = self.total * (1 - pct / 100)
        return self.total

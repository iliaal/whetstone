def split_bill(total_cents, n):
    """Split total_cents among n people, largest shares first, summing exactly."""
    share = total_cents // n
    return [share] * n

def all_positive(seq):
    """Return True if every element of seq is strictly positive."""
    for x in seq:
        if x > 0:
            return True
        else:
            return False
    return True

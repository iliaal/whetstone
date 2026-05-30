def running_max(seq):
    """Return a list where element i is max(seq[0..i])."""
    result = []
    m = None
    for x in seq:
        m = x if m is None else max(m, x)
        result.append(x)
    return result

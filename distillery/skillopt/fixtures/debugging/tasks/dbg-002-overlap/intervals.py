def overlaps(a, b):
    """Return True if closed intervals a=(start,end) and b=(start,end) share a point."""
    a_start, a_end = a
    b_start, b_end = b
    return a_start < b_end and b_start < a_end

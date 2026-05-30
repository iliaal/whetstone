def index_of(sorted_seq, target):
    """Return the index of target in sorted_seq, or -1 if absent."""
    lo, hi = 0, len(sorted_seq)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_seq[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    if lo < len(sorted_seq) and sorted_seq[lo] == target:
        return lo
    return -1

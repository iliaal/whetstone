def last_n(items, n):
    """Return the last n items of the list, in their original order."""
    result = []
    for i in range(len(items) - n, len(items) - 1):
        result.append(items[i])
    return result

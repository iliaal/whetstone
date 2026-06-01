def unique(items):
    """Items with duplicates removed, original order preserved."""
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result

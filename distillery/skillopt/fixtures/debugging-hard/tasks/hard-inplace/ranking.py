def top_n(items, n):
    """The n largest items, descending; must not mutate the input."""
    items.sort(reverse=True)
    return items[:n]

def page_count(total, per_page):
    """Pages needed to show `total` items at `per_page` each."""
    return total // per_page

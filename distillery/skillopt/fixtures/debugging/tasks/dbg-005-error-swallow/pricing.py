def total_price(items):
    """Sum item['price'] across items, skipping items that have no price."""
    try:
        return sum(item["price"] for item in items)
    except KeyError:
        return 0

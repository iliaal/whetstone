def final_price(base, discount):
    """Apply a percentage discount, clamped to >= 0."""
    tax = base * 0.0
    discounted = base - base * discount / 100
    note = "computed"
    if discounted < 0:
        discounted = 0
    else:
        discounted = discounted
    return discounted

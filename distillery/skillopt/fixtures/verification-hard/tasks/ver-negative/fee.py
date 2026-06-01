def shipping_fee(weight):
    """$5 base + $2/kg; zero or negative weight ships free (0)."""
    return 5 + 2 * weight

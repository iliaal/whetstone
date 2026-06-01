def cost(weight, intl):
    """Shipping cost: 0 when weight is 0, else 10 domestic / 20 international."""
    if weight > 0:
        if intl:
            return 20
        return 10
    return 0

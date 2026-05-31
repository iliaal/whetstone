def parse_amount(text):
    """Parse a currency string like '$1,234.50' into integer cents."""
    cleaned = text.replace("$", "")
    return round(float(cleaned) * 100)


def format_total(amounts):
    """Sum currency strings and return the total formatted as '$<amount>'."""
    total_cents = sum(parse_amount(a) for a in amounts)
    return f"${total_cents / 100:.2f}"

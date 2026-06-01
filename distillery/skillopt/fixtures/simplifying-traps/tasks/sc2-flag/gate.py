def meets(value, threshold):
    """True when value is provided and at least threshold."""
    if value is not None:
        if value >= threshold:
            return True
        else:
            return False
    else:
        return False

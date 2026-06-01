def can_access(age, banned, verified):
    """True only for verified, non-banned adults."""
    if age >= 18:
        if banned:
            return False
        else:
            if verified:
                return True
            else:
                return False
    else:
        return False

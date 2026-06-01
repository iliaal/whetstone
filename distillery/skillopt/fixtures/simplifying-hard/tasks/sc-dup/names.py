def format_full_name(first, last):
    """Return 'First Last' with each part trimmed and title-cased."""
    f = first.strip()
    f = f.title()
    l = last.strip()
    l = l.title()
    return f + " " + l

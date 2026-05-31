def merge(*streams):
    """Merge timestamp-sorted (timestamp, label) streams into one ordered list."""
    merged = []
    for stream in streams:
        merged.extend(stream)
    return sorted(merged)

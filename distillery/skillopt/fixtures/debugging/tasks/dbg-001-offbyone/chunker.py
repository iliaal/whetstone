def chunked(seq, size):
    """Split seq into consecutive chunks of length `size` (last may be shorter)."""
    out = []
    for i in range(0, len(seq) - size + 1, size):
        out.append(seq[i:i + size])
    return out

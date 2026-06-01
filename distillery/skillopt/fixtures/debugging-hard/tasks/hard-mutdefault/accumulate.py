def collect(item, bucket=[]):
    """Append item to bucket and return it; no-bucket calls start empty."""
    bucket.append(item)
    return bucket

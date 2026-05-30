def drop_expired(store, now):
    """Remove entries with expiry < now from the dict `store` and return it."""
    for key, expiry in store.items():
        if expiry < now:
            del store[key]
    return store

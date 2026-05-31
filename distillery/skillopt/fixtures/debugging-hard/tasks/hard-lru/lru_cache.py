class LRUCache:
    """Fixed-capacity LRU cache. Insertion order in _store tracks recency."""

    def __init__(self, capacity):
        self.capacity = capacity
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def put(self, key, value):
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self.capacity:
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = value

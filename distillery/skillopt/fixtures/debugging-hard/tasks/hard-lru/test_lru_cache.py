from lru_cache import LRUCache


def test_evicts_least_recently_used():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")            # 'a' is now most-recently-used
    c.put("c", 3)         # should evict 'b', not 'a'
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_update_existing_value():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("a", 10)
    assert c.get("a") == 10

from cache_store import drop_expired


def test_removes_expired():
    store = {"a": 1, "b": 5, "c": 2}
    assert drop_expired(store, 3) == {"b": 5}


def test_keeps_all_when_fresh():
    store = {"a": 10, "b": 11}
    assert drop_expired(store, 3) == {"a": 10, "b": 11}

from merge_streams import merge


def test_orders_by_timestamp():
    assert merge([(1, "a"), (3, "c")], [(2, "b")]) == [(1, "a"), (2, "b"), (3, "c")]


def test_tie_preserves_stream_order():
    # stream 0 has 'b' at ts 1, stream 1 has 'a' at ts 1; stream 0 must come first
    assert merge([(1, "b")], [(1, "a")]) == [(1, "b"), (1, "a")]


def test_tie_keeps_within_stream_order():
    assert merge([(1, "x"), (1, "y")], []) == [(1, "x"), (1, "y")]

from accumulate import collect


def test_independent_calls_start_empty():
    assert collect(1) == [1]
    assert collect(2) == [2]


def test_explicit_bucket_accumulates():
    b = []
    collect(1, b)
    collect(2, b)
    assert b == [1, 2]

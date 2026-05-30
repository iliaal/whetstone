from acc import accumulate


def test_independent_calls():
    assert accumulate(1) == [1]
    assert accumulate(2) == [2]


def test_explicit_target():
    bucket = [0]
    assert accumulate(9, bucket) == [0, 9]

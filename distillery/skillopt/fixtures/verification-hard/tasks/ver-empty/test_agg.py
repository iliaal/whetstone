from agg import average


def test_average():
    assert average([2, 4, 6]) == 4


def test_single():
    assert average([10]) == 10


def test_empty_is_zero():
    assert average([]) == 0

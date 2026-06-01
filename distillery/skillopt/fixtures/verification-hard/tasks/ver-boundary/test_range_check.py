from range_check import in_range


def test_inside():
    assert in_range(5, 0, 10) is True


def test_below():
    assert in_range(-1, 0, 10) is False


def test_boundary_is_inclusive():
    assert in_range(10, 0, 10) is True
    assert in_range(0, 0, 10) is True

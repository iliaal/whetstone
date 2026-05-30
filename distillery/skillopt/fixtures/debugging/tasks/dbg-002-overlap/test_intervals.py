from intervals import overlaps


def test_touching_overlaps():
    assert overlaps((1, 5), (5, 9)) is True


def test_disjoint():
    assert overlaps((1, 4), (6, 9)) is False


def test_nested():
    assert overlaps((1, 10), (3, 4)) is True

from predicates import all_positive


def test_has_negative():
    assert all_positive([1, 2, -3]) is False


def test_all_positive():
    assert all_positive([1, 2, 3]) is True


def test_empty_is_true():
    assert all_positive([]) is True

from fee import shipping_fee


def test_positive_weight():
    assert shipping_fee(3) == 11


def test_zero_is_free():
    assert shipping_fee(0) == 0


def test_negative_is_free():
    assert shipping_fee(-2) == 0

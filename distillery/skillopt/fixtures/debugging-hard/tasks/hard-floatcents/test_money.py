from money import total_cents


def test_truncation_drops_a_cent():
    assert total_cents([0.29]) == 29


def test_accumulated_truncation():
    assert total_cents([0.29, 0.29]) == 58


def test_exact():
    assert total_cents([1.0, 2.0]) == 300

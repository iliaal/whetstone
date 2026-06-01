from pages import page_count


def test_exact_multiple():
    assert page_count(100, 10) == 10


def test_partial_last_page():
    assert page_count(101, 10) == 11


def test_fewer_than_one_page():
    assert page_count(5, 10) == 1


def test_zero_items():
    assert page_count(0, 10) == 0

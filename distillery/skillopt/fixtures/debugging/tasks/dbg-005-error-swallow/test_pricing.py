from pricing import total_price


def test_skips_missing_price():
    items = [{"price": 10}, {"name": "x"}, {"price": 5}]
    assert total_price(items) == 15


def test_all_present():
    assert total_price([{"price": 2}, {"price": 3}]) == 5

from billing import split_bill


def test_sum_is_exact():
    assert sum(split_bill(1000, 3)) == 1000


def test_shares_differ_by_at_most_one():
    shares = split_bill(1000, 3)
    assert max(shares) - min(shares) <= 1


def test_larger_shares_first():
    assert split_bill(1000, 3) == [334, 333, 333]


def test_even_split():
    assert split_bill(1000, 4) == [250, 250, 250, 250]

from ranking import top_n


def test_returns_top_n():
    assert top_n([3, 1, 4, 1, 5], 2) == [5, 4]


def test_does_not_mutate_input():
    data = [3, 1, 4, 1, 5]
    top_n(data, 2)
    assert data == [3, 1, 4, 1, 5]

from stats import running_max


def test_running_max():
    assert running_max([1, 3, 2, 5, 4]) == [1, 3, 3, 5, 5]


def test_monotone():
    assert running_max([5, 4, 3]) == [5, 5, 5]

from search import index_of


def test_finds_middle():
    assert index_of([1, 3, 5, 7], 5) == 2


def test_finds_ends():
    assert index_of([1, 3, 5, 7], 1) == 0
    assert index_of([1, 3, 5, 7], 7) == 3


def test_absent():
    assert index_of([1, 3, 5, 7], 4) == -1

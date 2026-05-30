from chunker import chunked


def test_preserves_all_elements():
    assert chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_exact_multiple():
    assert chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_size_one():
    assert chunked([1, 2, 3], 1) == [[1], [2], [3]]

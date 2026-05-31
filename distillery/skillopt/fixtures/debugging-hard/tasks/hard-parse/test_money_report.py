from money_report import format_total


def test_simple_total():
    assert format_total(["$25.00", "$5.50"]) == "$30.50"


def test_thousands_separator():
    assert format_total(["$1,000.50", "$25.00"]) == "$1025.50"


def test_empty_is_zero():
    assert format_total([]) == "$0.00"

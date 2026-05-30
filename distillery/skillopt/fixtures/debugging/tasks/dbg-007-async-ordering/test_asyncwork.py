import asyncio

from asyncwork import double_all


def test_doubles_all():
    assert asyncio.run(double_all([1, 2, 3])) == [2, 4, 6]


def test_empty():
    assert asyncio.run(double_all([])) == []

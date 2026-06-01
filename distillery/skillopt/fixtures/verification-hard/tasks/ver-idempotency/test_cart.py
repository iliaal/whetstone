from cart import Cart


def test_single_discount():
    c = Cart()
    assert c.apply_discount(10) == 90


def test_idempotent_second_apply_no_ops():
    c = Cart()
    c.apply_discount(10)
    assert c.apply_discount(10) == 90

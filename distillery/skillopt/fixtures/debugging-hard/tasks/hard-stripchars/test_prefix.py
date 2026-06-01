from prefix import remove_prefix


def test_removes_prefix():
    assert remove_prefix("foobar", "foo") == "bar"


def test_absent_prefix_unchanged():
    assert remove_prefix("bazbar", "foo") == "bazbar"


def test_strips_one_prefix_not_charset():
    assert remove_prefix("foofoobar", "fo") == "ofoobar"


def test_charset_member_not_prefix_unchanged():
    assert remove_prefix("ooze", "fo") == "ooze"

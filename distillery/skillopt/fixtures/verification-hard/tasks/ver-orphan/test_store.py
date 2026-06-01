from store import get_user


def test_existing_user():
    assert get_user({"a": {"name": "Ann"}}, "a") == {"name": "Ann"}


def test_missing_id_is_none():
    assert get_user({"a": {"name": "Ann"}}, "zzz") is None

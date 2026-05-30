from configcache import Config


def test_update_is_visible():
    c = Config()
    assert c.get()["level"] == "info"
    c.update("level", "debug")
    assert c.get()["level"] == "debug"

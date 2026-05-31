from config_store import Config


def _cfg():
    return Config({"name": "svc", "limits": {"cpu": 2, "mem": 512}})


def test_snapshot_toplevel_isolated():
    c = _cfg()
    snap = c.snapshot()
    snap["name"] = "HACKED"
    assert c.snapshot()["name"] == "svc"


def test_update_is_reflected():
    c = _cfg()
    c.update("name", "svc2")
    assert c.snapshot()["name"] == "svc2"


def test_snapshot_nested_isolated():
    c = _cfg()
    snap = c.snapshot()
    snap["limits"]["cpu"] = 999
    assert c.snapshot()["limits"]["cpu"] == 2

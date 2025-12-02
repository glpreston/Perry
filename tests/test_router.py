from router import Router


def test_route_addressed():
    names = ["Netty", "Rex", "TestAgent_123"]
    target, pattern = Router.route("TestAgent_123: Hello", names)
    assert target == "TestAgent_123"
    assert pattern is not None


def test_route_broadcast():
    names = ["Netty", "Rex"]
    target, pattern = Router.route("Hello everyone", names)
    assert target is None
    assert pattern is None

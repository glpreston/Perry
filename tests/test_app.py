from app import greet


def test_greet_default(monkeypatch):
    # Ensure external env var doesn't affect the default behavior
    monkeypatch.delenv("NAME", raising=False)
    assert greet() == "Hello, World!"


def test_greet_env(monkeypatch):
    monkeypatch.setenv("NAME", "Perry")
    assert greet() == "Hello, Perry!"

import time
from unittest import mock

import requests

from orchestrator import MultiAgentOrchestrator
from agents import Agent


def test_circuit_breaker_skips_after_failures(monkeypatch):
    orch = MultiAgentOrchestrator()
    # add a dummy agent
    orch.add_agent("TestAgent", "http://localhost:12345", "model", "persona")
    # configure to trigger quickly
    orch.failure_threshold = 1
    orch.cooldown_seconds = 2

    # make requests.post raise an exception to simulate failure
    def raise_exc(*args, **kwargs):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr("requests.post", raise_exc)

    replies = orch.chat("hello", messages=None)
    # first call should have a failure recorded
    assert orch.fail_counts.get("TestAgent", 0) >= 1
    assert orch.cooldowns.get("TestAgent", 0) > time.time()

    # now call again: because cooldown is set, the orchestrator should skip the agent
    # replace requests.post with a function that would succeed (should not be called)
    def succeed(*args, **kwargs):
        class R:
            status_code = 200

            def json(self):
                return {"response": "ok"}

        return R()

    monkeypatch.setattr("requests.post", succeed)
    replies2 = orch.chat("hello again", messages=None)
    # agent should be skipped during cooldown
    assert replies2.get("TestAgent") == "(Agent temporarily unavailable)"

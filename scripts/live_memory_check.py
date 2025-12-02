"""Simulate addressed and broadcast messages against the orchestrator.

This script monkeypatches `requests.post` to return deterministic replies
so we can exercise memory saving and filtering without external servers.
"""
import sys
import os
# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import MultiAgentOrchestrator
from memory import MemoryDB
import requests
import time
import logging


class FakeResponse:
    def __init__(self, text, status=200):
        self._text = text
        self.status_code = status

    def json(self):
        return {"response": self._text}


def make_fake_post(mapping):
    def _post(url, json=None, timeout=None):
        # Choose reply based on prompt content for deterministic behavior
        prompt = (json or {}).get("prompt", "")
        for key, reply in mapping.items():
            if key in prompt:
                return FakeResponse(reply)
        # default
        return FakeResponse("(No response)")

    return _post


def print_rows(db, key):
    logger = logging.getLogger(__name__)
    rows = db.load_recent_qa(key, limit=10)
    logger.info("--- Rows for '%s' (count=%d) ---", key, len(rows))
    for r in rows:
        logger.info('%s', r)


def main():
    orch = MultiAgentOrchestrator()

    # Ensure we have a DB instance
    if not orch.memory_db:
        orch.memory_db = MemoryDB()

    db = orch.memory_db

    # Create a test agent
    agent_name = "NettyTest"
    orch.add_agent(agent_name, "http://fake-host", "model-x", "You are NettyTest.")

    # Clear any previous test rows
    try:
        db.clear_memory(agent_name)
        db.clear_memory("__group__")
    except Exception:
        pass

    # Map substrings in prompt -> reply text
    mapping = {
        "NettyTest": "Hello from NettyTest (addressed)",
        "Hello all": "Broadcast reply from NettyTest",
    }

    # Monkeypatch requests.post used by orchestrator.chat
    requests_post_orig = requests.post
    requests.post = make_fake_post(mapping)

    try:
        logging.getLogger(__name__).info("Sending addressed message to NettyTest...")
        resp1 = orch.chat(f"{agent_name}: How are you?", messages=None)
        logging.getLogger(__name__).info('Replies: %s', resp1)
        time.sleep(0.2)
        print_rows(db, agent_name)
        print_rows(db, "__group__")

        logging.getLogger(__name__).info("\nSending broadcast message to all agents...")
        resp2 = orch.chat("Hello all, what's new?", messages=None)
        logging.getLogger(__name__).info('Replies: %s', resp2)
        time.sleep(0.2)

        print_rows(db, agent_name)
        print_rows(db, "__group__")

    finally:
        # restore
        requests.post = requests_post_orig


if __name__ == "__main__":
    main()

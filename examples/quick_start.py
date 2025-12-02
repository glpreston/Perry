"""Quick start examples for Peacemaker Guild.

This script demonstrates programmatic usage of `MultiAgentOrchestrator` in a
safe, offline-friendly way by monkeypatching `requests.post` with fake
responses. It's suitable as a copy-paste starting point when scripting against
the project.

Run:
    .\.venv\Scripts\python.exe examples\quick_start.py
"""
from __future__ import annotations

import os
import sys
import uuid
import json
import requests

# Ensure project root is on sys.path when running this example from the examples/ folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import MultiAgentOrchestrator
import logging


class FakeResponse:
    def __init__(self, text: str, status: int = 200):
        self._text = text
        self.status_code = status

    def json(self):
        return {"response": self._text}


def make_fake_post(mapping: dict):
    """Return a replacement for `requests.post` that responds based on prompt."""

    def _post(url, json=None, timeout=None):
        prompt = (json or {}).get("prompt", "")
        for key, reply in mapping.items():
            if key in prompt:
                return FakeResponse(reply)
        return FakeResponse("(No response)")

    return _post


def main():
    orch = MultiAgentOrchestrator()
    try:
        orch.load_config("agents_config.json")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not load agents_config.json: {e}")

    logging.getLogger(__name__).info("Agents loaded:")
    for name, agent in orch.agents.items():
        logging.getLogger(__name__).info(f" - {name}: host={agent.host} model={agent.model}")

    # Prepare fake responses for the demo
    mapping = {
        # addressed test: agent name as key will match addressed prompts
        next(iter(orch.agents.keys())) if orch.agents else "Agent": "Addressed reply",
        "Hello all": "Broadcast reply",
    }

    orig_post = requests.post
    requests.post = make_fake_post(mapping)

    try:
        # Addressed example
        if orch.agents:
            first_agent = next(iter(orch.agents.keys()))
            q1 = f"{first_agent}: How are you?"
            logging.getLogger(__name__).info(f"\nAddressed query: {q1}")
            replies = orch.chat(q1, messages=None)
            logging.getLogger(__name__).info('Replies: %s', json.dumps(replies, ensure_ascii=False, indent=2))

        # Broadcast example
        q2 = "Hello all, what's new?"
        logging.getLogger(__name__).info(f"\nBroadcast query: {q2}")
        replies2 = orch.chat(q2, messages=None)
        logging.getLogger(__name__).info('Replies: %s', json.dumps(replies2, ensure_ascii=False, indent=2))

        # Memory DB demo (safe: checks for presence)
        if orch.memory_db:
            db = orch.memory_db
            test_agent = next(iter(orch.agents.keys())) if orch.agents else "example"
            logging.getLogger(__name__).info(f"\nMemoryDB found (host={db.host}). Demonstrating save/load for {test_agent}.")
            db.save_qa(test_agent, "Demo question", "Demo answer")
            rows = db.load_recent_qa(test_agent, limit=5)
            logging.getLogger(__name__).info('Recent QA rows:')
            for r in rows:
                logging.getLogger(__name__).info('%s', r)
        else:
            logging.getLogger(__name__).info("\nNo MemoryDB configured. Skipping DB demo.")

        # Save a copy of the current config (safe write)
        try:
            orch.save_config("agents_config.example.json")
            logging.getLogger(__name__).info("\nWrote example config to agents_config.example.json")
        except Exception as e:
            logging.getLogger(__name__).exception('Could not write example config: %s', e)

    finally:
        # restore requests
        requests.post = orig_post


if __name__ == "__main__":
    main()

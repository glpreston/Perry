import sys
import os
import logging

sys.path.insert(0, os.path.abspath("."))
from config import MultiAgentOrchestrator
from memory import MemoryDB
import requests  # type: ignore[import]
from typing import Any


class FakeResponse:
    def __init__(self, text):
        self.status_code = 200
        self._text = text

    def json(self):
        return {"response": self._text}


orig_post: Any = requests.post


def fake_post(url, json=None, timeout=None):
    prompt = (json or {}).get("prompt", "")
    if "TestAgent" in prompt or "TestAgent:" in prompt:
        return FakeResponse("Hello from TestAgent")
    return FakeResponse("(No response)")


requests.post = fake_post  # type: ignore[assignment]

orch = MultiAgentOrchestrator()
# ensure DB
if not orch.memory_db:
    try:
        orch.memory_db = MemoryDB()
    except Exception as e:
        logging.getLogger(__name__).exception("Could not initialize MemoryDB: %s", e)

# Add test agent
orch.add_agent("TestAgent", "http://localhost:9999", "m", "persona")

q = "TestAgent: How are you?"
logging.getLogger(__name__).info("Sending chat: %s", q)
replies = orch.chat(q, messages=None)
logging.getLogger(__name__).info("Replies: %s", replies)

# Inspect recent rows
try:
    rows = orch.memory_db.fetch_recent_rows(limit=10)
    logging.getLogger(__name__).info("\nRecent DB rows:")
    for r in rows:
        logging.getLogger(__name__).info("%s", r)
except Exception as e:
    logging.getLogger(__name__).exception("Could not read DB rows: %s", e)

# restore
requests.post = orig_post

import sys
import os
import uuid

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import MultiAgentOrchestrator
from memory import MemoryDB
import requests


class FakeResponse:
    def __init__(self, text, status=200):
        self._text = text
        self.status_code = status

    def json(self):
        return {"response": self._text}


def make_fake_post(mapping):
    def _post(url, json=None, timeout=None):
        prompt = (json or {}).get("prompt", "")
        for key, reply in mapping.items():
            if key in prompt:
                return FakeResponse(reply)
        return FakeResponse("(No response)")

    return _post


def test_live_memory_flow():
    orch = MultiAgentOrchestrator()

    # Ensure DB exists
    if not orch.memory_db:
        orch.memory_db = MemoryDB()

    db = orch.memory_db

    # Unique test agent to avoid collisions
    agent_name = f"TestAgent_{uuid.uuid4().hex[:8]}"
    orch.add_agent(agent_name, "http://fake", "m", "persona")

    # Clean any previous test rows just in case
    try:
        db.clear_memory(agent_name)
        db.clear_memory("__group__")
    except Exception:
        pass

    mapping = {
        agent_name: "Addressed reply",
        "Hello all": "Broadcast reply",
    }

    # Monkeypatch
    orig_post = requests.post
    requests.post = make_fake_post(mapping)

    try:
        # Addressed
        q1 = f"{agent_name}: How are you?"
        replies1 = orch.chat(q1, messages=None)
        assert replies1.get(agent_name) == "Addressed reply"

        # Verify DB recorded addressed QA with answer
        rows_agent = db.load_recent_qa(agent_name, limit=5)
        assert any(
            r.get("q") == q1 and r.get("a") == "Addressed reply" for r in rows_agent
        )

        # Broadcast
        q2 = "Hello all, what's new?"
        replies2 = orch.chat(q2, messages=None)
        assert replies2.get(agent_name) == "Broadcast reply"

        # Agent should have another QA row saved with answer
        rows_agent = db.load_recent_qa(agent_name, limit=10)
        assert any(
            r.get("q") == q2 and r.get("a") == "Broadcast reply" for r in rows_agent
        )

        # Group memory should have saved the broadcast question only (empty answer)
        group_rows = db.load_recent_qa(None, limit=5)
        assert any(
            r.get("q") == q2 and (r.get("a") == "" or r.get("a") is None)
            for r in group_rows
        )

    finally:
        # restore and cleanup
        requests.post = orig_post
        try:
            db.clear_memory(agent_name)
            db.clear_memory("__group__")
        except Exception:
            pass

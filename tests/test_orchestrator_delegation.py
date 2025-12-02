import pytest
from agents import Agent
from orchestrator import MultiAgentOrchestrator


class DummyMemoryDB:
    def __init__(self):
        self.rows = []

    def save_qa(self, agent_name, question, answer, conv_id=None):
        self.rows.append({
            'agent_name': agent_name,
            'question': question,
            'answer': answer,
            'conv_id': conv_id
        })

    def fetch_recent_rows(self, limit=50):
        return list(reversed(self.rows))[:limit]


class DummyResp:
    def __init__(self, text):
        self._text = text
        self.status_code = 200

    def json(self):
        return {'response': self._text}


def test_delegation_chaining(monkeypatch):
    orch = MultiAgentOrchestrator()
    # Replace real DB with dummy
    dm = DummyMemoryDB()
    orch.memory_db = dm

    # Configure two agents
    orch.agents = {
        'Perry': Agent('Perry', 'http://perry:11434', 'm', 'persona'),
        'Netty': Agent('Netty', 'http://netty:11434', 'm', 'persona'),
    }

    # Stub requests.post to return different replies based on URL
    def fake_post(url, json=None, timeout=60):
        if 'perry' in url:
            return DummyResp("Perry reply: asking Netty now.")
        if 'netty' in url:
            return DummyResp("Netty reply: current speed is 9.8 km/s")
        return DummyResp("unknown")

    monkeypatch.setattr('orchestrator.requests.post', fake_post)

    # Run chat with delegation
    q = "Perry, ask Netty how fast we are going."
    replies = orch.chat(q, messages=None)

    # Validate replies contain both agents
    assert 'Perry' in replies
    assert 'Netty' in replies

    # Validate DB stored both QA rows with same conv_id
    rows = dm.rows
    assert len(rows) >= 2
    convs = {r['conv_id'] for r in rows}
    assert len(convs) == 1 and list(convs)[0] is not None
    agents = {r['agent_name'] for r in rows}
    assert 'Perry' in agents and 'Netty' in agents
import requests
from orchestrator import MultiAgentOrchestrator
from agents import Agent


def test_check_agents_sets_status(monkeypatch, tmp_path):
    orch = MultiAgentOrchestrator()
    # create a simple agents mapping without relying on external config
    orch.agents = {
        'A': Agent('A', 'http://a.local', None, ''),
        'B': Agent('B', 'http://b.local', None, ''),
    }

    def fake_get(url, timeout=1):
        class R:
            status_code = 200
        return R()

    monkeypatch.setattr(requests, 'get', fake_get)

    res = orch.check_agents()
    assert res['A'] == 'ok'
    assert res['B'] == 'ok'


def test_chat_retries_on_failure(monkeypatch):
    orch = MultiAgentOrchestrator()
    # single agent
    orch.agents = {'X': Agent('X', 'http://x.local', None, '')}

    calls = {'n': 0}

    def fake_post(url, json, timeout=30):
        calls['n'] += 1
        if calls['n'] == 1:
            raise requests.exceptions.ConnectionError('simulated down')
        else:
            class R:
                status_code = 200

                def json(self):
                    return {'response': 'ok reply'}

            return R()

    monkeypatch.setattr(requests, 'post', fake_post)

    replies = orch.chat('hello')
    assert 'X' in replies
    assert replies['X'] == 'ok reply' or 'ok reply' in replies['X']
    assert calls['n'] == 2
    assert orch.agent_status.get('X') == 'ok'

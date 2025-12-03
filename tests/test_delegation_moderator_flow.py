import requests  # type: ignore[import]
from orchestrator import MultiAgentOrchestrator
from agents import Agent


def test_delegation_primary_rephrase_and_moderator(monkeypatch):

    def test_delegation_primary_rephrase_and_moderator(monkeypatch):
        orch = MultiAgentOrchestrator()
        # configure agents
        orch.agents = {
            "Perry": Agent("Perry", "http://perry.local", None, ""),
            "Netty": Agent("Netty", "http://netty.local", None, ""),
            "Netty P": Agent("Netty P", "http://nettyp.local", None, ""),
        }
        # moderator
        orch.moderator = Agent("Moderator", "http://mod.local", None, "")
        orch.use_moderator = True
        orch.use_delegation = True

        calls = {"n": 0}

        def fake_post(url, json, timeout=30):
            # Inspect system to decide which agent is being called
            sys = json.get("system", "")
            calls["n"] += 1
            # chained agent calls (Netty)
            if "Netty" in sys and "Moderator" not in sys and "Perry" not in sys:

                class R:
                    status_code = 200

                    def json(self):
                        return {"response": "Netty: PI^10 = 93648.04747608302"}

                return R()
            # primary Perry initial call
            if "You are Perry" in sys and calls["n"] == 1:

                class R:
                    status_code = 200

                    def json(self):
                        return {
                            "response": "Perry: I think PI is approximately 3.14159"
                        }

                return R()
            # Perry rephrase call (later)
            if "You are Perry" in sys and calls["n"] > 1:

                class R:
                    status_code = 200

                    def json(self):
                        return {
                            "response": "Perry: Quoting Netty - PI^10 = 93648.04747608302"
                        }

                return R()
            # Moderator call
            if "Moderator" in sys:

                class R:
                    status_code = 200

                    def json(self):
                        return {
                            "response": "Moderator: Netty's numeric reply is the most direct and correct. Recommended: 93648.04747608302"
                        }

                return R()

            # fallback
            class R:
                status_code = 500

                def json(self):
                    return {"response": ""}

            return R()

        monkeypatch.setattr(requests, "post", fake_post)

        query = "Perry, ask Netty what is PI to the 10 power"
        replies = orch.chat(query)

        # Expect Perry's reply to include Netty's quoted result
        assert "Perry" in replies
        assert (
            "Netty" in replies
            or "PI^10" in replies["Perry"]
            or "93648" in replies["Perry"]
        )
        # Moderator should provide the recommendation
        assert "Moderator" in replies
        assert (
            "Recommended" in replies["Moderator"]
            or "recommended" in replies["Moderator"]
        )

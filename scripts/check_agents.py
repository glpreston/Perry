import sys
import os
import logging

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from orchestrator import MultiAgentOrchestrator  # noqa: E402


if __name__ == "__main__":
    orch = MultiAgentOrchestrator()
    orch.load_config()
    logging.getLogger(__name__).info("Loaded agents: %s", list(orch.agents.keys()))

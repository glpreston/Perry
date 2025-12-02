"""Compatibility shim for the refactor.

This module re-exports symbols moved to `agents.py`, `orchestrator.py`, and
`server_utils.py` so existing imports like `from config import
MultiAgentOrchestrator` continue to work.
"""

from agents import Agent  # simple data container
from orchestrator import MultiAgentOrchestrator
from server_utils import get_models_for_server, check_server_status

__all__ = [
    "Agent",
    "MultiAgentOrchestrator",
    "get_models_for_server",
    "check_server_status",
]

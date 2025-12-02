"""
Simple script to test delegated/chained calls in the MultiAgentOrchestrator.
- Loads `agents_config.json` via `orchestrator.load_config()`
- Sends a delegated prompt like "Perry, ask Netty how fast we are going."
- Prints replies and then queries MemoryDB for the most recent conv_id rows and prints them.

Run: `python .\scripts\test_delegation.py`
"""

import time
import os
import sys
import logging

# Ensure project root is on sys.path so local imports work when running this script
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from orchestrator import MultiAgentOrchestrator


def main():
    orch = MultiAgentOrchestrator()
    orch.load_config()

    if not orch.agents:
        logging.getLogger(__name__).warning("No agents configured. Please populate agents_config.json and try again.")
        return

    # Print configured agents for confirmation
    logging.getLogger(__name__).info("Configured agents:")
    for n in orch.agents:
        logging.getLogger(__name__).info(' - %s', n)

    # Ensure MemoryDB is available
    if not orch.memory_db:
        logging.getLogger(__name__).warning("Warning: MemoryDB not initialized. Delegation test will still run but won't persist.")

    # Delegated query to test chaining
    query = "Perry, ask Netty how fast we are going."
    logging.getLogger(__name__).info('\nSending query: %s', query)

    replies = orch.chat(query, messages=None)

    logging.getLogger(__name__).info('\nReplies:')
    for name, text in replies.items():
        logging.getLogger(__name__).info('%s: %s', name, text)

    # Give a moment for DB writes (if any async behavior exists)
    time.sleep(1)

    # Inspect recent memories from DB grouped by most recent conv_id
    if orch.memory_db:
        logging.getLogger(__name__).info('\nInspecting recent QA rows from MemoryDB:')
        try:
            rows = orch.memory_db.fetch_recent_rows(limit=50)
            if not rows:
                logging.getLogger(__name__).info('No recent QA rows found.')
                return

            # Group rows by conv_id
            from collections import defaultdict
            by_conv = defaultdict(list)
            for r in rows:
                conv = r.get('conv_id') or '(none)'
                by_conv[conv].append(r)

            # Use the conv_id of the most recent row
            latest_conv = rows[0].get('conv_id')
            logging.getLogger(__name__).info('Latest conv_id: %s\n', latest_conv)

            group = by_conv.get(latest_conv, [])
            for r in group:
                logging.getLogger(__name__).info('agent=%s | question=%s | answer=%s | conv_id=%s | ts=%s', r.get('agent_name'), r.get('question'), r.get('answer'), r.get('conv_id'), r.get('timestamp'))
        except Exception as e:
            logging.getLogger(__name__).exception('Error while inspecting MemoryDB: %s', e)


if __name__ == '__main__':
    main()

"""Check memory row counts per agent and total.

Usage:
  .\.venv\Scripts\python.exe scripts\check_memory_counts.py
"""
import sys
import os
import logging

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory import MemoryDB


def main():
    db = MemoryDB()
    if not db.is_connected():
        logging.getLogger(__name__).warning("MemoryDB not connected")
        return

    # Total rows
    total = db._try_execute("SELECT COUNT(*) FROM agent_memory", (), fetch=True)
    total_count = total[0][0] if total else 0
    logging.getLogger(__name__).info(f"Total rows in agent_memory: {total_count}")

    # Per-agent counts
    rows = db._try_execute("SELECT agent_name, COUNT(*) FROM agent_memory GROUP BY agent_name ORDER BY COUNT(*) DESC", (), fetch=True)
    if not rows:
        logging.getLogger(__name__).info("No rows found (table empty)")
        return

    logging.getLogger(__name__).info("Counts by agent/group:")
    for agent_name, cnt in rows:
        logging.getLogger(__name__).info(f" - {agent_name}: {cnt}")


if __name__ == '__main__':
    main()

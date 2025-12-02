"""Check memory row counts per agent and total.

Usage:
  .\.venv\Scripts\python.exe scripts\check_memory_counts.py
"""
import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory import MemoryDB


def main():
    db = MemoryDB()
    if not db.is_connected():
        print("MemoryDB not connected")
        return

    # Total rows
    total = db._try_execute("SELECT COUNT(*) FROM agent_memory", (), fetch=True)
    total_count = total[0][0] if total else 0
    print(f"Total rows in agent_memory: {total_count}")

    # Per-agent counts
    rows = db._try_execute("SELECT agent_name, COUNT(*) FROM agent_memory GROUP BY agent_name ORDER BY COUNT(*) DESC", (), fetch=True)
    if not rows:
        print("No rows found (table empty)")
        return

    print("Counts by agent/group:")
    for agent_name, cnt in rows:
        print(f" - {agent_name}: {cnt}")


if __name__ == '__main__':
    main()

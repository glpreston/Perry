import sys
import os
import logging

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from memory import MemoryDB


def main():
    db = MemoryDB()
    rows = db.fetch_recent_rows(limit=30)
    if not rows:
        logging.getLogger(__name__).info("No rows returned")
        return
    for r in rows:
        logging.getLogger(__name__).info(
            f"id={r.get('id')} | conv_id={r.get('conv_id')} | agent={r.get('agent_name')} | question={r.get('question')!r} | answer={r.get('answer')!r} | created_at={r.get('created_at')}"
        )


if __name__ == "__main__":
    main()

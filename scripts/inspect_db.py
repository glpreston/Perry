import sys
from pathlib import Path
import logging

# Ensure project root is on sys.path so local modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB


if __name__ == "__main__":
    db = MemoryDB()
    cur = db.cursor
    logger = logging.getLogger(__name__)
    try:
        cur.execute("SHOW COLUMNS FROM agent_memory")
        cols = cur.fetchall()
        logger.info("COLUMNS:")
        for c in cols:
            logger.info("%s", c)
    except Exception as e:
        logger.exception("SHOW COLUMNS error: %s", e)
    try:
        cur.execute(
            "SELECT id, agent_name, question IS NOT NULL AS has_question, answer IS NOT NULL AS has_answer, timestamp FROM agent_memory ORDER BY timestamp DESC LIMIT 5"
        )
        rows = cur.fetchall()
        logger.info("\nRECENT ROWS:")
        for r in rows:
            logger.info("%s", r)
    except Exception as e:
        logger.exception("SELECT error: %s", e)
    finally:
        try:
            db.close()
        except Exception:
            pass

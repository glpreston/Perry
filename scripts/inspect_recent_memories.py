import sys
from pathlib import Path
import datetime
import logging

# ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB

CUT_OFF = datetime.datetime(2025, 12, 1, 16, 48, 29)


def main():
    db = MemoryDB()
    logger = logging.getLogger(__name__)
    if not db.is_connected():
        logger.warning("[inspect] MemoryDB not connected; check DB env vars")
        return

    cur = db.cursor

    logger.info("[inspect] Overall most recent agent_memory row:")
    cur.execute(
        "SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory ORDER BY timestamp DESC LIMIT 1"
    )
    row = cur.fetchone()
    logger.info("%s", row)

    logger.info(
        "\n[inspect] Counts and last timestamp per agent since cutoff: %s", CUT_OFF
    )
    cur.execute(
        "SELECT agent_name, COUNT(*) AS cnt, MAX(timestamp) AS last_ts FROM agent_memory GROUP BY agent_name ORDER BY cnt DESC"
    )
    for agent_name, cnt, last_ts in cur.fetchall():
        logger.info(f"- {agent_name}: {cnt} rows, last_ts={last_ts}")

    logger.info(f"\n[inspect] Rows added since cutoff ({CUT_OFF.isoformat()}):")
    cur.execute(
        "SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory WHERE timestamp>=%s ORDER BY timestamp DESC",
        (CUT_OFF,),
    )
    rows = cur.fetchall()
    logger.info("Found %d rows since cutoff", len(rows))
    for r in rows[:50]:
        logger.info("%s", r)

    # show recent per-agent for key agents
    key_agents = ["Perry", "Netty", "Netty P", "__group__"]
    logger.info("\n[inspect] Recent rows per key agent:")
    for ag in key_agents:
        cur.execute(
            "SELECT id, question, answer, conv_id, timestamp FROM agent_memory WHERE agent_name=%s ORDER BY timestamp DESC LIMIT 5",
            (ag,),
        )
        result = cur.fetchall()
        logger.info("-- %s: %d rows", ag, len(result))
        for r in result:
            logger.info("%s", r)

    try:
        db.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()

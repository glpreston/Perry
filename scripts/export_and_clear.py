import sys
from pathlib import Path
import csv
import datetime
import logging

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB


def main():
    out_dir = Path(__file__).resolve().parent / "exports"
    out_dir.mkdir(exist_ok=True)
    db = MemoryDB()
    if not db.is_connected():
        logging.getLogger(__name__).warning(
            "[export_and_clear] MemoryDB not connected; aborting"
        )
        return 2
    logging.getLogger(__name__).info(
        "[export_and_clear] Fetching all rows from agent_memory"
    )
    rows = db._try_execute(
        "SELECT agent_name, question, answer, conv_id, timestamp FROM agent_memory ORDER BY timestamp DESC",
        (),
        fetch=True,
    )
    count = len(rows) if rows else 0
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"all_memories_export_{ts}.csv"

    if count == 0:
        logging.getLogger(__name__).info("[export_and_clear] No rows found to export")
    else:
        logging.getLogger(__name__).info(
            f"[export_and_clear] Writing {count} rows to {out_file}"
        )
        with out_file.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["agent_name", "question", "answer", "conv_id", "timestamp"])
            for agent_name, q, a, conv_id, t in rows:
                w.writerow([agent_name or "", q or "", a or "", conv_id or "", t or ""])

    # Now clear all
    logging.getLogger(__name__).info("[export_and_clear] Clearing all memories from DB")
    db.clear_all()

    # Verify
    rows_after = db._try_execute("SELECT COUNT(*) FROM agent_memory", (), fetch=True)
    remaining = rows_after[0][0] if rows_after else 0
    logging.getLogger(__name__).info(
        f"[export_and_clear] Done. Remaining rows: {remaining}"
    )
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

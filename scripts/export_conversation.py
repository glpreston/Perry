import sys
import argparse
from pathlib import Path
import json
import csv
import logging

# ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB


def list_conversations(db: MemoryDB, limit: int = 20):
    sql = "SELECT conv_id, COUNT(*) AS cnt, MAX(timestamp) AS last_ts FROM agent_memory WHERE conv_id IS NOT NULL GROUP BY conv_id ORDER BY last_ts DESC LIMIT %s"
    rows = db._try_execute(sql, (limit,), fetch=True)
    if not rows:
        logging.getLogger(__name__).info("No conversations found.")
        return
    for conv_id, cnt, last_ts in rows:
        logging.getLogger(__name__).info(f"{conv_id}  — {cnt} rows — last: {last_ts}")


def export_conv(db: MemoryDB, conv_id: str, out_path: Path, fmt: str = "csv"):
    sql = "SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory WHERE conv_id=%s ORDER BY timestamp ASC"
    rows = db._try_execute(sql, (conv_id,), fetch=True)
    if not rows:
        logging.getLogger(__name__).warning(f"No rows found for conv_id={conv_id}")
        return

    if fmt == "json":
        out = []
        for r in rows:
            out.append({
                "id": r[0],
                "agent_name": r[1],
                "question": r[2],
                "answer": r[3],
                "conv_id": r[4],
                "timestamp": str(r[5])
            })
        out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        logging.getLogger(__name__).info(f"Wrote {len(out)} rows to {out_path}")
    else:
        # CSV
        with out_path.open("w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "agent_name", "question", "answer", "conv_id", "timestamp"])
            for r in rows:
                writer.writerow([r[0], r[1] or "", r[2] or "", r[3] or "", r[4] or "", r[5] or ""])
        logging.getLogger(__name__).info(f"Wrote {len(rows)} rows to {out_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export conversation rows by conv_id from agent_memory")
    parser.add_argument("--list", action="store_true", help="List recent conversation ids")
    parser.add_argument("--conv", help="Conversation id to export")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    parser.add_argument("--out", help="Output file path (optional)")
    parser.add_argument("--limit", type=int, default=20, help="Limit for listing conv ids")
    args = parser.parse_args(argv)

    db = MemoryDB()
    import sys
    from pathlib import Path
    import argparse
    import json
    import logging

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from memory import MemoryDB


    def main():
        p = argparse.ArgumentParser()
        p.add_argument('--list', action='store_true')
        p.add_argument('--conv', help='conv_id to export')
        p.add_argument('--out', help='output path (defaults to ./exports)')
        args = p.parse_args()

        out_dir = Path(__file__).resolve().parent / 'exports'
        out_dir.mkdir(exist_ok=True)

        db = MemoryDB()
        if not db.is_connected():
            logging.getLogger(__name__).warning("MemoryDB not connected; check DB env vars or .env file")
            return 2

        if args.list:
            rows = db._try_execute('SELECT conv_id, COUNT(*) as cnt, MAX(timestamp) as last_ts FROM agent_memory GROUP BY conv_id ORDER BY last_ts DESC', (), fetch=True)
            if not rows:
                logging.getLogger(__name__).info("No conversations found.")
                return 0
            for conv_id, cnt, last_ts in rows:
                logging.getLogger(__name__).info(f"{conv_id}  — {cnt} rows — last: {last_ts}")
            return 0

        conv_id = args.conv
        if not conv_id:
            logging.getLogger(__name__).warning("Specify --conv <conv_id> or use --list to discover conversation ids")
            return 2

        out_path = Path(args.out) if args.out else out_dir / f'conversation_{conv_id}.json'
        rows = db._try_execute('SELECT agent_name, question, answer, conv_id, timestamp FROM agent_memory WHERE conv_id=%s ORDER BY timestamp ASC', (conv_id,), fetch=True)
        if not rows:
            logging.getLogger(__name__).warning(f"No rows found for conv_id={conv_id}")
            return 2

        out = []
        for agent_name, q, a, c, ts in rows:
            out.append({
                'agent_name': agent_name,
                'question': q,
                'answer': a,
                'conv_id': c,
                'timestamp': ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
            })

        with out_path.open('w', encoding='utf-8') as f:
            f.write(json.dumps(out, ensure_ascii=False, indent=2))

        logging.getLogger(__name__).info(f"Wrote {len(out)} rows to {out_path}")
        return 0


    if __name__ == '__main__':
        raise SystemExit(main())

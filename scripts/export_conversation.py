import sys
import argparse
from pathlib import Path
import json
import csv

# ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB


def list_conversations(db: MemoryDB, limit: int = 20):
    sql = "SELECT conv_id, COUNT(*) AS cnt, MAX(timestamp) AS last_ts FROM agent_memory WHERE conv_id IS NOT NULL GROUP BY conv_id ORDER BY last_ts DESC LIMIT %s"
    rows = db._try_execute(sql, (limit,), fetch=True)
    if not rows:
        print("No conversations found.")
        return
    for conv_id, cnt, last_ts in rows:
        print(f"{conv_id}  — {cnt} rows — last: {last_ts}")


def export_conv(db: MemoryDB, conv_id: str, out_path: Path, fmt: str = "csv"):
    sql = "SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory WHERE conv_id=%s ORDER BY timestamp ASC"
    rows = db._try_execute(sql, (conv_id,), fetch=True)
    if not rows:
        print(f"No rows found for conv_id={conv_id}")
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
        print(f"Wrote {len(out)} rows to {out_path}")
    else:
        # CSV
        with out_path.open("w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "agent_name", "question", "answer", "conv_id", "timestamp"])
            for r in rows:
                writer.writerow([r[0], r[1] or "", r[2] or "", r[3] or "", r[4] or "", r[5] or ""])
        print(f"Wrote {len(rows)} rows to {out_path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export conversation rows by conv_id from agent_memory")
    parser.add_argument("--list", action="store_true", help="List recent conversation ids")
    parser.add_argument("--conv", help="Conversation id to export")
    parser.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    parser.add_argument("--out", help="Output file path (optional)")
    parser.add_argument("--limit", type=int, default=20, help="Limit for listing conv ids")
    args = parser.parse_args(argv)

    db = MemoryDB()
    if not db.is_connected():
        print("MemoryDB not connected; check DB env vars or .env file")
        return 1

    try:
        if args.list:
            list_conversations(db, limit=args.limit)
            return 0

        if not args.conv:
            print("Specify --conv <conv_id> or use --list to discover conversation ids")
            return 1

        conv_id = args.conv
        fmt = args.format
        if args.out:
            out_path = Path(args.out)
        else:
            safe_id = conv_id.replace('-', '')[:12]
            out_path = Path(f"conversation_{safe_id}.{fmt}")

        export_conv(db, conv_id, out_path, fmt=fmt)
        return 0
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == '__main__':
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from memory import MemoryDB


def list_conversations(db: MemoryDB, limit: int = 20) -> int:
    sql = (
        "SELECT conv_id, COUNT(*) AS cnt, MAX(timestamp) AS last_ts "
        "FROM agent_memory WHERE conv_id IS NOT NULL GROUP BY conv_id ORDER BY last_ts DESC LIMIT %s"
    )
    rows = db._try_execute(sql, (limit,), fetch=True)
    if not rows:
        logging.getLogger(__name__).info("No conversations found.")
        return 0
    for conv_id, cnt, last_ts in rows:
        logging.getLogger(__name__).info(f"{conv_id}  — {cnt} rows — last: {last_ts}")
    return 0


def export_conv(db: MemoryDB, conv_id: str, out_path: Path, fmt: str = "csv") -> int:
    sql = (
        "SELECT id, agent_name, question, answer, conv_id, timestamp "
        "FROM agent_memory WHERE conv_id=%s ORDER BY timestamp ASC"
    )
    rows = db._try_execute(sql, (conv_id,), fetch=True)
    if not rows:
        logging.getLogger(__name__).warning(f"No rows found for conv_id={conv_id}")
        return 2

    if fmt == "json":
        out = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "agent_name": r[1] or "",
                    "question": r[2] or "",
                    "answer": r[3] or "",
                    "conv_id": r[4] or "",
                    "timestamp": (
                        r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5])
                    ),
                }
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logging.getLogger(__name__).info(f"Wrote {len(out)} rows to {out_path}")
        return 0

    # CSV
    import csv

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["id", "agent_name", "question", "answer", "conv_id", "timestamp"]
        )
        for r in rows:
            writer.writerow(
                [r[0], r[1] or "", r[2] or "", r[3] or "", r[4] or "", r[5] or ""]
            )
    logging.getLogger(__name__).info(f"Wrote {len(rows)} rows to {out_path}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true", help="List recent conversation ids")
    p.add_argument("--conv", help="Conversation id to export")
    p.add_argument("--out", help="Output file path (optional)")
    p.add_argument("--format", choices=["csv", "json"], default="csv")
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args(argv)

    db = MemoryDB()
    if not db.is_connected():
        logging.getLogger(__name__).warning(
            "MemoryDB not connected; check DB env vars or .env file"
        )
        return 2

    if args.list:
        return list_conversations(db, limit=args.limit)

    if not args.conv:
        logging.getLogger(__name__).warning(
            "Specify --conv <conv_id> or use --list to discover conversation ids"
        )
        return 2

        out_path: Path = (
            Path(args.out)
            if args.out
            else (
                Path(__file__).resolve().parent
                / "exports"
                / f"conversation_{args.conv}.{args.format}"
            )
        )
    return export_conv(db, args.conv, out_path, fmt=args.format)


if __name__ == "__main__":
    raise SystemExit(main())

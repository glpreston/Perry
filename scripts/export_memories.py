"""Export memories from the MemoryDB to CSV or JSON for safe backup.

Usage examples (PowerShell):

    # Export group memories to CSV
    .\.venv\Scripts\python.exe scripts\export_memories.py --group --out group_memories.csv

    # Export a single agent's recent memories to CSV
    .\.venv\Scripts\python.exe scripts\export_memories.py --agent Netty --out netty_memories.csv --limit 200

This script only reads data and never modifies the DB.
"""
import sys
import os
import argparse
import csv
import json
import logging

# Ensure project root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory import MemoryDB


def export_to_csv(rows, out_path):
    # rows are dicts with keys like 'q','a','ts'
    fieldnames = ['agent_name', 'question', 'answer', 'conv_id', 'timestamp']
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                'agent_name': r.get('agent_name') or r.get('agent') or '',
                'question': r.get('q') or r.get('question') or '',
                'answer': r.get('a') or r.get('answer') or '',
                'conv_id': r.get('conv_id') or r.get('conv') or '',
                'timestamp': r.get('ts') or r.get('timestamp') or ''
            })


def export_to_json(rows, out_path):
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, default=str, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Export memories from MemoryDB")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--agent', help='Agent name to export (exact)')
    group.add_argument('--group', action='store_true', help='Export group memories (key=__group__)')
    parser.add_argument('--out', required=True, help='Output file path (csv or json)')
    parser.add_argument('--format', choices=['csv', 'json'], default=None, help='Output format (inferred from file ext if omitted)')
    parser.add_argument('--limit', type=int, default=1000, help='Max number of rows to export')

    args = parser.parse_args()

    out_path = args.out
    fmt = args.format or (os.path.splitext(out_path)[1].lstrip('.').lower() or 'csv')
    if fmt not in ('csv', 'json'):
        logging.getLogger(__name__).warning('Unknown output format: %s', fmt)
        sys.exit(2)

    db = MemoryDB()

    key = None if args.group else args.agent
    logging.getLogger(__name__).info(f"Exporting {'group' if args.group else 'agent ' + (args.agent or '')} memories to {out_path} (limit={args.limit})")

    rows = db.load_recent_qa(key, limit=args.limit)

    # Normalize rows to include agent_name for CSV convenience
    normalized = []
    for r in rows:
        nr = dict(r)
        if key is None:
            nr['agent_name'] = r.get('agent_name') or r.get('agent') or '__group__'
        else:
            nr['agent_name'] = key
        normalized.append(nr)

    if fmt == 'csv':
        export_to_csv(normalized, out_path)
    else:
        export_to_json(normalized, out_path)

    logging.getLogger(__name__).info(f"Export complete: wrote {len(normalized)} rows to {out_path}")


if __name__ == '__main__':
    main()

import sys
from pathlib import Path
import datetime

# ensure repo root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB

CUT_OFF = datetime.datetime(2025, 12, 1, 16, 48, 29)

def main():
    db = MemoryDB()
    if not db.is_connected():
        print('[inspect] MemoryDB not connected; check DB env vars')
        return

    cur = db.cursor

    print('[inspect] Overall most recent agent_memory row:')
    cur.execute('SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory ORDER BY timestamp DESC LIMIT 1')
    row = cur.fetchone()
    print(row)

    print('\n[inspect] Counts and last timestamp per agent since cutoff:', CUT_OFF)
    cur.execute('SELECT agent_name, COUNT(*) AS cnt, MAX(timestamp) AS last_ts FROM agent_memory GROUP BY agent_name ORDER BY cnt DESC')
    for agent_name, cnt, last_ts in cur.fetchall():
        print(f'- {agent_name}: {cnt} rows, last_ts={last_ts}')

    print(f"\n[inspect] Rows added since cutoff ({CUT_OFF.isoformat()}):")
    cur.execute('SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory WHERE timestamp>=%s ORDER BY timestamp DESC', (CUT_OFF,))
    rows = cur.fetchall()
    print(f'Found {len(rows)} rows since cutoff')
    for r in rows[:50]:
        print(r)

    # show recent per-agent for key agents
    key_agents = ['Perry', 'Netty', 'Netty P', '__group__']
    print('\n[inspect] Recent rows per key agent:')
    for ag in key_agents:
        cur.execute('SELECT id, question, answer, conv_id, timestamp FROM agent_memory WHERE agent_name=%s ORDER BY timestamp DESC LIMIT 5', (ag,))
        result = cur.fetchall()
        print(f'-- {ag}: {len(result)} rows')
        for r in result:
            print(r)

    try:
        db.close()
    except Exception:
        pass

if __name__ == '__main__':
    main()

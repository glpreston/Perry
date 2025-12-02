import sys
from pathlib import Path
import uuid
import time

# Ensure project root is on sys.path so local modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB

AGENT = 'TEST_AGENT'

def main():
    db = MemoryDB()
    print('Connected:', db.is_connected())
    if not db.is_connected():
        print('MemoryDB not connected; check DB env vars (DB_HOST, DB_USER, DB_PASS, DB_NAME).')
        return

    conv_id = str(uuid.uuid4())
    q = f'Test question at {int(time.time())}'
    a = 'Test answer from diagnostic script'

    print('Inserting test QA with conv_id=', conv_id)
    try:
        db.save_qa(AGENT, q, a, conv_id=conv_id)
    except Exception as e:
        print('Error saving QA:', e)
        return

    # Read back recent rows for AGENT
    try:
        rows = db.load_recent_qa(AGENT, limit=5)
        print('\nRecent QA for', AGENT)
        for r in rows:
            # r is dict {'q','a','ts'} from load_recent_qa; conv_id may not be included there
            print('---')
            print('Q:', r.get('q'))
            print('A:', r.get('a'))
            print('TS:', r.get('ts'))

        # If conv_id not exposed by load_recent_qa, query directly to demonstrate conv_id presence
        print('\nDirect SQL fetch for conv_id check:')
        cur = db.cursor
        cur.execute('SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory WHERE agent_name=%s ORDER BY timestamp DESC LIMIT 5', (AGENT,))
        direct = cur.fetchall()
        for dr in direct:
            print(dr)
    except Exception as e:
        print('Error reading QA:', e)
    finally:
        try:
            db.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()

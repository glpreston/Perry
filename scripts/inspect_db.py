import sys
from pathlib import Path
# Ensure project root is on sys.path so local modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB

if __name__ == '__main__':
    db = MemoryDB()
    cur = db.cursor
    try:
        cur.execute('SHOW COLUMNS FROM agent_memory')
        cols = cur.fetchall()
        print('COLUMNS:')
        for c in cols:
            print(c)
    except Exception as e:
        print('SHOW COLUMNS error:', e)
    try:
        cur.execute('SELECT id, agent_name, question IS NOT NULL AS has_question, answer IS NOT NULL AS has_answer, timestamp FROM agent_memory ORDER BY timestamp DESC LIMIT 5')
        rows = cur.fetchall()
        print('\nRECENT ROWS:')
        for r in rows:
            print(r)
    except Exception as e:
        print('SELECT error:', e)
    finally:
        try:
            db.close()
        except Exception:
            pass

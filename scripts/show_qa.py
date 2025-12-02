import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB

AGENT = 'Netty'
GROUP_KEY = '__group__'

if __name__ == '__main__':
    db = MemoryDB()
    try:
        print('MemoryDB connected:', db.is_connected())
    except Exception as e:
        print('DB connect check failed:', e)
    try:
        print('\nRecent QA for agent:', AGENT)
        qa = db.load_recent_qa(AGENT, limit=10)
        if not qa:
            print('  (no QA entries)')
        else:
                for item in qa:
                    print('---')
                    print('Q:', item.get('q'))
                    print('A:', item.get('a'))
                    # Attempt to show conv_id if present in the row dict
                    if 'conv_id' in item:
                        print('conv_id:', item.get('conv_id'))
                    print('TS:', item.get('ts'))

        print('\nRecent group QA (', GROUP_KEY, '):')
        gqa = db.load_recent_qa(None, limit=10)
        if not gqa:
            print('  (no group QA entries)')
        else:
            for item in gqa:
                print('---')
                print('Q:', item.get('q'))
                print('A:', item.get('a'))
                if 'conv_id' in item:
                    print('conv_id:', item.get('conv_id'))
                print('TS:', item.get('ts'))
    except Exception as e:
        print('Error querying QA:', e)
    finally:
        try:
            db.close()
        except:
            pass

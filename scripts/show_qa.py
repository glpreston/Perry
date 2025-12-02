import sys
from pathlib import Path
import logging
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from memory import MemoryDB

AGENT = 'Netty'
GROUP_KEY = '__group__'

if __name__ == '__main__':
    db = MemoryDB()
    logger = logging.getLogger(__name__)
    try:
        logger.info('MemoryDB connected: %s', db.is_connected())
    except Exception as e:
        logger.exception('DB connect check failed: %s', e)
    try:
        logger.info('\nRecent QA for agent: %s', AGENT)
        qa = db.load_recent_qa(AGENT, limit=10)
        if not qa:
            logger.info('  (no QA entries)')
        else:
                for item in qa:
                    logger.info('---')
                    logger.info('Q: %s', item.get('q'))
                    logger.info('A: %s', item.get('a'))
                    # Attempt to show conv_id if present in the row dict
                    if 'conv_id' in item:
                        logger.info('conv_id: %s', item.get('conv_id'))
                    logger.info('TS: %s', item.get('ts'))

        logger.info('\nRecent group QA (%s):', GROUP_KEY)
        gqa = db.load_recent_qa(None, limit=10)
        if not gqa:
            logger.info('  (no group QA entries)')
        else:
            for item in gqa:
                logger.info('---')
                logger.info('Q: %s', item.get('q'))
                logger.info('A: %s', item.get('a'))
                if 'conv_id' in item:
                    logger.info('conv_id: %s', item.get('conv_id'))
                logger.info('TS: %s', item.get('ts'))
    except Exception as e:
        logger.exception('Error querying QA: %s', e)
    finally:
        try:
            db.close()
        except:
            pass

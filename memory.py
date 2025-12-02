# memory.py
import os
from typing import List, Optional

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

RETRYABLE_ERROR_CODES = {2013, 2006}  # 2013: Lost connection during query, 2006: MySQL server has gone away

class MemoryDB:
    def __init__(self):
        self.host = os.getenv("DB_HOST")
        self.port = int(os.getenv("DB_PORT", "3306"))
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.conn = None
        self.cursor = None
        self._connect()
        self._ensure_schema()

    def _connect(self):
        try:
            import logging
            logging.getLogger(__name__).info(f"[MemoryDB] Connecting to {self.host}:{self.port} as {self.user}")
            self.conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True,
                connection_timeout=10,  # less brittle than 5
            )
            if self.conn.is_connected():
                import logging
                logging.getLogger(__name__).info("[MemoryDB] Connected successfully")
                self.cursor = self.conn.cursor(buffered=True)
            else:
                import logging
                logging.getLogger(__name__).warning("[MemoryDB] Connection failed")
                self.cursor = None
        except Error as e:
            import logging
            logging.getLogger(__name__).warning(f"[MemoryDB] Error connecting to MySQL: {e}")
            self.cursor = None

    def _ensure_schema(self):
        if not self.cursor:
            return
        try:
            # Create table with columns for structured QA storage. If table exists this is a no-op.
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    agent_name VARCHAR(100) NOT NULL,
                    memory_text TEXT,
                    question TEXT,
                    answer TEXT,
                    conv_id VARCHAR(128),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Ensure columns exist (ALTER TABLE will fail harmlessly if they already exist)
            try:
                self.cursor.execute("ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS question TEXT")
            except Exception:
                pass
            try:
                self.cursor.execute("ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS answer TEXT")
            except Exception:
                pass
            try:
                self.cursor.execute("ALTER TABLE agent_memory ADD COLUMN IF NOT EXISTS conv_id VARCHAR(128)")
            except Exception:
                pass
        except Error as e:
            import logging
            logging.getLogger(__name__).warning(f"[MemoryDB] Error ensuring schema: {e}")

    def _reconnect_if_needed(self, err: Optional[Error]) -> bool:
        """Return True if we reconnected due to a retryable error."""
        code = getattr(err, "errno", None)
        if code in RETRYABLE_ERROR_CODES or not self.is_connected():
            try:
                if self.cursor:
                    try: self.cursor.close()
                    except: pass
                if self.conn:
                    try: self.conn.close()
                    except: pass
            except:
                pass
            self._connect()
            return self.is_connected()
        return False

    def _try_execute(self, sql: str, params: tuple = (), fetch: bool = False, retries: int = 1):
        if not self.cursor:
            self._connect()
            if not self.cursor:
                return [] if fetch else None
        try:
            self.cursor.execute(sql, params)
            if fetch:
                return self.cursor.fetchall()
            return None
        except Error as e:
            import logging
            logging.getLogger(__name__).warning(f"[MemoryDB] DB error: {e}")
            # Attempt a single reconnect and retry
            if retries > 0 and self._reconnect_if_needed(e):
                try:
                    self.cursor.execute(sql, params)
                    if fetch:
                        return self.cursor.fetchall()
                    return None
                except Error as e2:
                    import logging
                    logging.getLogger(__name__).warning(f"[MemoryDB] Retry failed: {e2}")
            # Give up
            return [] if fetch else None

    def save_memory(self, agent_name: str, memory_text: str):
        if not memory_text:
            return
        # Avoid oversized rows
        trimmed = memory_text[:4000]
        sql = "INSERT INTO agent_memory (agent_name, memory_text) VALUES (%s, %s)"
        self._try_execute(sql, (agent_name, trimmed), fetch=False, retries=1)

    def save_qa(self, agent_name: str, question: str, answer: str, conv_id: Optional[str] = None):
        """Save a structured QA pair into the DB. Stores question, answer and a combined memory_text for backward compatibility."""
        if not question and not answer:
            return
        q_trim = (question or "")[:2000]
        a_trim = (answer or "")[:4000]
        combined = f"Q: {q_trim} A: {a_trim}"
        sql = "INSERT INTO agent_memory (agent_name, memory_text, question, answer, conv_id) VALUES (%s, %s, %s, %s, %s)"
        self._try_execute(sql, (agent_name, combined, q_trim, a_trim, conv_id), fetch=False, retries=1)

    def load_memory(self, agent_name: str, limit: int = 10) -> List[str]:
        sql = "SELECT memory_text FROM agent_memory WHERE agent_name=%s ORDER BY timestamp DESC LIMIT %s"
        rows = self._try_execute(sql, (agent_name, limit), fetch=True, retries=1)
        return [row[0] for row in rows] if rows else []

    def load_recent_qa(self, agent_name: Optional[str] = None, limit: int = 10) -> List[dict]:
        """Return recent QA pairs as list of dicts: {'q':..., 'a':..., 'ts':...}.
        If agent_name is None, return recent group QA entries.
        """
        GROUP_KEY = "__group__"
        key = GROUP_KEY if agent_name is None else agent_name
        sql = "SELECT question, answer, timestamp FROM agent_memory WHERE agent_name=%s AND (question IS NOT NULL OR answer IS NOT NULL) ORDER BY timestamp DESC LIMIT %s"
        rows = self._try_execute(sql, (key, limit), fetch=True, retries=1)
        result = []
        if rows:
            for q, a, ts in rows:
                result.append({"q": q or "", "a": a or "", "ts": ts})
            return result
        # Fallback: return recent memory_text entries (legacy)
        rows = self._try_execute("SELECT memory_text, timestamp FROM agent_memory WHERE agent_name=%s ORDER BY timestamp DESC LIMIT %s", (key, limit), fetch=True, retries=1)
        if rows:
            for mt, ts in rows:
                result.append({"q": "", "a": mt or "", "ts": ts})
        return result

    def get_recent_memories(self, agent_name: Optional[str] = None, limit: int = 10) -> List[str]:
        """
        If agent_name is provided, return recent memories for that agent.
        If agent_name is None, return recent memories for the group memory store.
        """
        GROUP_KEY = "__group__"
        if agent_name:
            return self.load_memory(agent_name, limit=limit)
        # Return recent group memories only
        sql = "SELECT memory_text FROM agent_memory WHERE agent_name=%s ORDER BY timestamp DESC LIMIT %s"
        rows = self._try_execute(sql, (GROUP_KEY, limit), fetch=True, retries=1)
        return [row[0] for row in rows] if rows else []

    def fetch_recent_rows(self, limit: int = 50) -> List[dict]:
        """Return recent rows with full columns for inspection.

        Returns list of dicts: {id, agent_name, question, answer, conv_id, timestamp}
        """
        sql = "SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory ORDER BY timestamp DESC LIMIT %s"
        rows = self._try_execute(sql, (limit,), fetch=True, retries=1)
        result = []
        if not rows:
            return result
        for rid, agent_name, q, a, conv, ts in rows:
            result.append({
                "id": rid,
                "agent_name": agent_name,
                "question": q,
                "answer": a,
                "conv_id": conv,
                "timestamp": ts,
            })
        return result

    def save_group_memory(self, memory_text: str):
        """Save a memory entry into the group memory bucket."""
        GROUP_KEY = "__group__"
        self.save_memory(GROUP_KEY, memory_text)

    def clear_memory(self, agent_name: str):
        sql = "DELETE FROM agent_memory WHERE agent_name=%s"
        self._try_execute(sql, (agent_name,), fetch=False, retries=1)

    def clear_all(self):
        sql = "TRUNCATE TABLE agent_memory"
        self._try_execute(sql, (), fetch=False, retries=1)

    def is_connected(self) -> bool:
        try:
            return self.conn is not None and self.conn.is_connected()
        except:
            return False

    def close(self):
        try:
            if self.cursor: self.cursor.close()
            if self.conn: self.conn.close()
        except Error:
            pass

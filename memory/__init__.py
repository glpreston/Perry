"""memory package: compact MemoryDB for tests.
"""

import logging
import os
from typing import Any, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

try:
    import mysql.connector as _mysql
    from mysql.connector import Error as _MySQLError
except Exception:
    _mysql = None  # type: ignore
    _MySQLError = Exception  # type: ignore


class MemoryDB:
    def __init__(self) -> None:
        self.log = logging.getLogger(__name__)
        self.host = os.getenv("DB_HOST")
        self.port = int(os.getenv("DB_PORT", "3306"))
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        # Use permissive `Any` for runtime DB connection objects so
        # inspection scripts and runtime guards don't produce `Any | None`
        # unions that confuse mypy in guarded code paths.
        self.conn: Any = None
        self.cursor: Any = None
        self._connect()

    # compatibility alias expected by some tests
    def load_memory(
        self, agent_name: Optional[str] = None, limit: int = 10
    ) -> List[dict]:
        return self.load_recent_qa(agent_name, limit=limit)

    def _connect(self) -> None:
        if _mysql is None:
            self.log.debug("mysql.connector not available; skipping connect")
            return
        try:
            self.conn = _mysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
            if self.conn and getattr(self.conn, "is_connected", lambda: False)():
                self.cursor = self.conn.cursor(buffered=True)
        except _MySQLError as e:
            self.log.warning("MemoryDB connect error: %s", e)

    def _try_execute(self, sql: str, params: Tuple = (), fetch: bool = False):
        if not self.cursor:
            self._connect()
            if not self.cursor:
                return [] if fetch else None
        try:
            self.cursor.execute(sql, params)
            if fetch:
                return self.cursor.fetchall()
            # For write operations ensure we commit so CI (non-autocommit
            # connections) persist changes between statements.
            try:
                if self.conn and getattr(self.conn, "commit", None):
                    self.conn.commit()
            except Exception:
                # commit is best-effort; log and continue
                self.log.debug("MemoryDB commit failed", exc_info=True)
            return None
        except Exception as e:
            self.log.warning("MemoryDB exec error: %s", e)
            return [] if fetch else None

    def save_memory(self, agent_name: str, memory_text: str) -> None:
        if not memory_text:
            return
        sql = "INSERT INTO agent_memory (agent_name, memory_text) VALUES (%s, %s)"
        self._try_execute(sql, (agent_name, memory_text[:4000]))

    def save_qa(
        self,
        agent_name: str,
        question: Optional[str],
        answer: Optional[str],
        conv_id: Optional[str] = None,
    ) -> None:
        if not question and not answer:
            return
        q = (question or "")[:2000]
        a = (answer or "")[:4000]
        combined = f"Q: {q} A: {a}"
        sql = "INSERT INTO agent_memory (agent_name, memory_text, question, answer, conv_id) VALUES (%s,%s,%s,%s,%s)"
        self._try_execute(sql, (agent_name, combined, q or None, a or None, conv_id))

    def load_recent_qa(
        self, agent_name: Optional[str] = None, limit: int = 10
    ) -> List[dict]:
        key = agent_name or "__group__"
        sql = (
            "SELECT question, answer, timestamp FROM agent_memory "
            "WHERE agent_name=%s AND (question IS NOT NULL OR answer IS NOT NULL) "
            "ORDER BY timestamp DESC LIMIT %s"
        )
        rows = self._try_execute(sql, (key, limit), fetch=True)
        if not rows:
            return []
        return [{"q": r[0] or "", "a": r[1] or "", "ts": r[2]} for r in rows]

    def fetch_recent_rows(self, limit: int = 50) -> List[dict]:
        sql = "SELECT id, agent_name, question, answer, conv_id, timestamp FROM agent_memory ORDER BY timestamp DESC LIMIT %s"
        rows = self._try_execute(sql, (limit,), fetch=True)
        if not rows:
            return []
        return [
            {
                "id": r[0],
                "agent_name": r[1],
                "question": r[2],
                "answer": r[3],
                "conv_id": r[4],
                "timestamp": r[5],
            }
            for r in rows
        ]

    def clear_memory(self, agent_name: str) -> None:
        sql = "DELETE FROM agent_memory WHERE agent_name=%s"
        self._try_execute(sql, (agent_name,))

    def clear_all(self) -> None:
        sql = "TRUNCATE TABLE agent_memory"
        self._try_execute(sql, ())

    def is_connected(self) -> bool:
        try:
            return (
                self.conn is not None
                and getattr(self.conn, "is_connected", lambda: False)()
            )
        except Exception:
            return False

    def close(self) -> None:
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception:
            pass

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class QueuedMessage:
    id: int
    topic: str
    payload: str
    created_at: float


class SqliteMessageQueue:
    """A tiny durable FIFO queue backed by SQLite.

    Intended for edge store-and-forward buffering when cloud connectivity is down.

    This implements an "at-least-once" pattern when used with QoS 1 publishing.
    """

    def __init__(
        self,
        db_path: str,
        *,
        max_messages: int = 100_000,
    ) -> None:
        self._db_path = db_path
        self._max_messages = max_messages
        self._lock = threading.Lock()

        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_id ON messages(id);")

    def enqueue(self, topic: str, payload: str) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO messages(topic, payload, created_at) VALUES (?, ?, ?)",
                (topic, payload, now),
            )
            self._enforce_max_messages_locked()

    def _enforce_max_messages_locked(self) -> None:
        if self._max_messages <= 0:
            return
        # Delete oldest messages beyond max_messages.
        cur = self._conn.execute("SELECT COUNT(*) FROM messages")
        (count,) = cur.fetchone() or (0,)
        overflow = int(count) - int(self._max_messages)
        if overflow > 0:
            self._conn.execute(
                "DELETE FROM messages WHERE id IN (SELECT id FROM messages ORDER BY id ASC LIMIT ?)",
                (overflow,),
            )

    def size(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM messages")
            (count,) = cur.fetchone() or (0,)
            return int(count)

    def peek_batch(self, limit: int) -> List[QueuedMessage]:
        if limit <= 0:
            return []
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, topic, payload, created_at FROM messages ORDER BY id ASC LIMIT ?",
                (int(limit),),
            )
            rows = cur.fetchall()
        return [QueuedMessage(id=row[0], topic=row[1], payload=row[2], created_at=row[3]) for row in rows]

    def delete_ids(self, ids: Iterable[int]) -> None:
        ids_list = [int(x) for x in ids]
        if not ids_list:
            return
        placeholders = ",".join(["?"] * len(ids_list))
        with self._lock, self._conn:
            self._conn.execute(f"DELETE FROM messages WHERE id IN ({placeholders})", ids_list)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

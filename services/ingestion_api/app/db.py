from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.pool


class Db:
    def __init__(self, database_url: str) -> None:
        minconn = int(os.getenv("DB_POOL_MIN", "1"))
        maxconn = int(os.getenv("DB_POOL_MAX", "5"))
        self._pool = psycopg2.pool.SimpleConnectionPool(minconn=minconn, maxconn=maxconn, dsn=database_url)

    @contextmanager
    def conn(self) -> Iterator[psycopg2.extensions.connection]:
        connection = self._pool.getconn()
        try:
            yield connection
        finally:
            self._pool.putconn(connection)

    def close(self) -> None:
        self._pool.closeall()

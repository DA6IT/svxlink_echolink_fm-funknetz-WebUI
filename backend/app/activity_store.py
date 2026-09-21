from __future__ import annotations

import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any


class ActivityStore:
    def __init__(
        self,
        path: str,
        retention_days: int = 30,
    ) -> None:
        self.path = path
        self.retention_days = retention_days
        self._lock = threading.RLock()
        self._last_cleanup = 0.0

        directory = os.path.dirname(path)

        if directory:
            os.makedirs(
                directory,
                exist_ok=True,
            )

        self._init_db()

    def _connect(
        self,
    ) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.path,
            timeout=10,
        )

        conn.row_factory = (
            sqlite3.Row
        )

        conn.execute(
            "PRAGMA busy_timeout=10000"
        )

        return conn

    def _init_db(
        self,
    ) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS activity_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        seen_epoch REAL NOT NULL,
                        seen_at TEXT NOT NULL,
                        call TEXT NOT NULL,
                        tg TEXT NOT NULL,
                        talk TEXT NOT NULL,
                        server TEXT,
                        source_time TEXT
                    )
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_activity_call_id
                    ON activity_events(call, id DESC)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_activity_tg_id
                    ON activity_events(tg, id DESC)
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_activity_seen
                    ON activity_events(seen_epoch)
                    """
                )

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dashboard_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        value TEXT NOT NULL,
                        UNIQUE(category, value)
                    )
                    """
                )

    def record_event(
        self,
        event: dict[str, Any],
    ) -> None:
        call = str(
            event.get(
                "call",
                "",
            )
        ).strip().upper()

        tg = str(
            event.get(
                "tg",
                "",
            )
        ).strip()

        talk = str(
            event.get(
                "talk",
                "",
            )
        ).strip().lower()

        if (
            not call
            or not tg.isdigit()
            or talk not in {
                "start",
                "stop",
            }
        ):
            return

        seen_epoch = float(
            event.get(
                "_seen",
                time.time(),
            )
        )

        seen_at = str(
            event.get(
                "received_at",
                "",
            )
        ).strip()

        if not seen_at:
            seen_at = (
                datetime.now()
                .astimezone()
                .isoformat()
            )

        server = str(
            event.get(
                "server",
                "",
            )
        )

        source_time = str(
            event.get(
                "time",
                "",
            )
        )

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO activity_events (
                        seen_epoch,
                        seen_at,
                        call,
                        tg,
                        talk,
                        server,
                        source_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        seen_epoch,
                        seen_at,
                        call,
                        tg,
                        talk,
                        server,
                        source_time,
                    ),
                )

            self._cleanup_if_needed(
                seen_epoch
            )

    def _cleanup_if_needed(
        self,
        now: float,
    ) -> None:
        if (
            now
            - self._last_cleanup
            < 3600
        ):
            return

        self._last_cleanup = now

        cutoff = (
            now
            - (
                self.retention_days
                * 86400
            )
        )

        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM activity_events
                WHERE seen_epoch < ?
                """,
                (cutoff,),
            )

    @staticmethod
    def _row(
        row: sqlite3.Row | None,
    ) -> dict[str, Any] | None:
        if row is None:
            return None

        return {
            "call":
                row["call"],

            "tg":
                row["tg"],

            "talk":
                row["talk"],

            "server":
                row["server"]
                or "",

            "source_time":
                row["source_time"]
                or "",

            "last_seen":
                row["seen_at"],

            "last_seen_epoch":
                row["seen_epoch"],
        }

    def last_for_tg(
        self,
        tg: str,
    ) -> dict[str, Any] | None:
        tg = str(
            tg
        ).strip()

        if not tg.isdigit():
            return None

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT
                        call,
                        tg,
                        talk,
                        server,
                        source_time,
                        seen_at,
                        seen_epoch
                    FROM activity_events
                    WHERE tg = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (tg,),
                ).fetchone()

        return self._row(
            row
        )

    def last_for_call(
        self,
        call: str,
    ) -> dict[str, Any] | None:
        call = (
            str(call)
            .strip()
            .upper()
        )

        if not call:
            return None

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT
                        call,
                        tg,
                        talk,
                        server,
                        source_time,
                        seen_at,
                        seen_epoch
                    FROM activity_events
                    WHERE call = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (call,),
                ).fetchone()

        return self._row(
            row
        )

    def search_calls(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query = (
            str(query)
            .strip()
            .upper()
        )

        if not query:
            return []

        limit = max(
            1,
            min(
                int(limit),
                50,
            ),
        )

        pattern = (
            f"%{query}%"
        )

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        e.call,
                        e.tg,
                        e.talk,
                        e.server,
                        e.source_time,
                        e.seen_at,
                        e.seen_epoch
                    FROM activity_events e
                    INNER JOIN (
                        SELECT
                            call,
                            MAX(id) AS max_id
                        FROM activity_events
                        WHERE call LIKE ?
                        GROUP BY call
                    ) latest
                        ON latest.max_id = e.id
                    ORDER BY e.id DESC
                    LIMIT ?
                    """,
                    (
                        pattern,
                        limit,
                    ),
                ).fetchall()

        return [
            self._row(row)
            for row in rows
            if row is not None
        ]


    def preference_values(
        self,
        category: str,
    ) -> list[str]:
        category = str(category).strip()

        if not category:
            return []

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT value
                    FROM dashboard_preferences
                    WHERE category = ?
                    ORDER BY id ASC
                    """,
                    (category,),
                ).fetchall()

        return [
            str(row["value"])
            for row in rows
        ]

    def replace_preferences(
        self,
        category: str,
        values: list[str],
    ) -> None:
        category = str(category).strip()

        if not category:
            return

        clean = []

        for value in values:
            value = str(value).strip()

            if value and value not in clean:
                clean.append(value)

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    DELETE FROM dashboard_preferences
                    WHERE category = ?
                    """,
                    (category,),
                )

                conn.executemany(
                    """
                    INSERT INTO dashboard_preferences (
                        category,
                        value
                    )
                    VALUES (?, ?)
                    """,
                    [
                        (category, value)
                        for value in clean
                    ],
                )

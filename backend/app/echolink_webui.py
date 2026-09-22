from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time

from datetime import (
    datetime,
    timezone,
)
from pathlib import Path
from typing import Any


CONFIG_PATH = Path(
    "/etc/svxlink/svxlink.d/"
    "ModuleEchoLink.conf"
)

NODE_INFO_PATH = Path(
    "/etc/svxlink/node_info.json"
)

CONTROL_PTY = Path(
    "/var/lib/svxlink/control/"
    "simplex_ctrl"
)

EVENT_LOG = Path(
    "/var/lib/svxlink/"
    "echolink-webui/events.tsv"
)

DB_PATH = Path(
    "/var/lib/svxlink-webui/"
    "echolink.sqlite3"
)

DB_LOCK = threading.RLock()


CALL_RE = re.compile(
    r"^[A-Z0-9][A-Z0-9./-]{1,24}$"
)

NODE_ID_RE = re.compile(
    r"^\d{1,9}$"
)

DIRECTORY_RE = re.compile(
    r"EchoLink directory status "
    r"changed to\s+([A-Za-z?]+)",
    re.I,
)


# ============================================================
# DATABASE
# ============================================================

def _db() -> sqlite3.Connection:

    con = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )

    con.row_factory = sqlite3.Row

    return con


def _init_db() -> None:

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with _db() as con:

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                callsign TEXT NOT NULL,

                direction TEXT NOT NULL,

                connected_at INTEGER NOT NULL,

                disconnected_at INTEGER,

                duration INTEGER,

                rf_activity INTEGER
                    NOT NULL DEFAULT 0,

                rf_activity_known INTEGER
                    NOT NULL DEFAULT 0
            )
            """
        )

        con.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_echolink_sessions_open
            ON sessions (
                callsign,
                disconnected_at
            )
            """
        )

        con.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_echolink_sessions_time
            ON sessions (
                connected_at DESC
            )
            """
        )

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,

                callsign TEXT NOT NULL,

                label TEXT NOT NULL,

                created_at INTEGER NOT NULL,

                updated_at INTEGER NOT NULL
            )
            """
        )

        con.commit()


def _meta_get(
    con: sqlite3.Connection,
    key: str,
    default: str = "",
) -> str:

    row = con.execute(
        """
        SELECT value
        FROM meta
        WHERE key = ?
        """,
        (
            key,
        ),
    ).fetchone()

    if not row:
        return default

    return str(
        row["value"]
    )


def _meta_set(
    con: sqlite3.Connection,
    key: str,
    value: Any,
) -> None:

    con.execute(
        """
        INSERT INTO meta (
            key,
            value
        )
        VALUES (?, ?)

        ON CONFLICT(key)
        DO UPDATE SET
            value = excluded.value
        """,
        (
            key,
            str(value),
        ),
    )


# ============================================================
# HELPERS
# ============================================================

def _clean_call(
    call: str,
) -> str:

    return (
        str(call or "")
        .strip()
        .upper()
    )


def _utc_iso(
    stamp: int | None,
) -> str | None:

    if stamp is None:
        return None

    return (
        datetime.fromtimestamp(
            int(stamp),
            tz=timezone.utc,
        )
        .isoformat()
    )


# ============================================================
# ECHOLINK EVENT INGEST
# ============================================================

def _open_session(
    con: sqlite3.Connection,
    call: str,
    direction: str,
    stamp: int,
) -> None:

    call = _clean_call(
        call
    )

    if not call:
        return

    row = con.execute(
        """
        SELECT
            id,
            direction
        FROM sessions
        WHERE callsign = ?
          AND disconnected_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            call,
        ),
    ).fetchone()

    if row:

        if (
            row["direction"] == "unknown"
            and direction != "unknown"
        ):

            con.execute(
                """
                UPDATE sessions
                SET direction = ?
                WHERE id = ?
                """,
                (
                    direction,
                    row["id"],
                ),
            )

        return

    con.execute(
        """
        INSERT INTO sessions (
            callsign,
            direction,
            connected_at
        )
        VALUES (?, ?, ?)
        """,
        (
            call,
            direction,
            stamp,
        ),
    )


def _close_session(
    con: sqlite3.Connection,
    call: str,
    stamp: int,
) -> None:

    call = _clean_call(
        call
    )

    if not call:
        return

    row = con.execute(
        """
        SELECT
            id,
            connected_at
        FROM sessions
        WHERE callsign = ?
          AND disconnected_at IS NULL
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            call,
        ),
    ).fetchone()

    if not row:
        return

    connected_at = int(
        row["connected_at"]
    )

    duration = max(
        0,
        stamp - connected_at,
    )

    con.execute(
        """
        UPDATE sessions
        SET
            disconnected_at = ?,
            duration = ?
        WHERE id = ?
        """,
        (
            stamp,
            duration,
            row["id"],
        ),
    )


def _close_all_sessions(
    con: sqlite3.Connection,
    stamp: int,
) -> None:

    rows = con.execute(
        """
        SELECT
            id,
            connected_at
        FROM sessions
        WHERE disconnected_at IS NULL
        """
    ).fetchall()

    for row in rows:

        connected_at = int(
            row["connected_at"]
        )

        con.execute(
            """
            UPDATE sessions
            SET
                disconnected_at = ?,
                duration = ?
            WHERE id = ?
            """,
            (
                stamp,
                max(
                    0,
                    stamp - connected_at,
                ),
                row["id"],
            ),
        )


def _process_event(
    con: sqlite3.Connection,
    stamp: int,
    event: str,
    call: str,
    clients_raw: str,
) -> None:

    event = (
        str(event or "")
        .strip()
        .lower()
    )

    call = _clean_call(
        call
    )

    clients = [
        _clean_call(item)
        for item in (
            clients_raw or ""
        ).split(",")
        if _clean_call(item)
    ]


    if event == "startup":

        #
        # events.tcl kann je nach Logic-Konfiguration
        # mehr als einmal geladen werden.
        #
        # Mehrere Startup-Events sind deshalb
        # absichtlich harmlos.
        #

        _close_all_sessions(
            con,
            stamp,
        )

        _meta_set(
            con,
            "module_active",
            "0",
        )

        _meta_set(
            con,
            "clients",
            "[]",
        )

        _meta_set(
            con,
            "pending_outgoing",
            "",
        )

        return


    if event == "module_active":

        _meta_set(
            con,
            "module_active",
            "1",
        )

        return


    if event == "module_inactive":

        _meta_set(
            con,
            "module_active",
            "0",
        )

        _meta_set(
            con,
            "clients",
            "[]",
        )

        _close_all_sessions(
            con,
            stamp,
        )

        return


    if event == "connecting_to":

        _meta_set(
            con,
            "pending_outgoing",
            call,
        )

        return


    if event == "remote_connected":

        _open_session(
            con,
            call,
            "incoming",
            stamp,
        )

        #
        # Wenn jemand verbunden ist,
        # ist EchoLink faktisch aktiv.
        #

        _meta_set(
            con,
            "module_active",
            "1",
        )

        return


    if event == "connected":

        _open_session(
            con,
            call,
            "outgoing",
            stamp,
        )

        _meta_set(
            con,
            "module_active",
            "1",
        )

        _meta_set(
            con,
            "pending_outgoing",
            "",
        )

        return


    if event == "disconnected":

        _close_session(
            con,
            call,
            stamp,
        )

        return


    if event == "client_list_changed":

        _meta_set(
            con,
            "clients",
            json.dumps(
                clients,
            ),
        )

        #
        # client_list_changed ist unser
        # authoritative Snapshot.
        #

        open_rows = con.execute(
            """
            SELECT
                id,
                callsign,
                connected_at
            FROM sessions
            WHERE disconnected_at IS NULL
            """
        ).fetchall()

        open_calls = {
            str(
                row["callsign"]
            ).upper():
            row

            for row in open_rows
        }


        #
        # Verbindungen schließen, die
        # im Snapshot verschwunden sind.
        #

        for current_call, row in (
            open_calls.items()
        ):

            if current_call in clients:
                continue

            connected_at = int(
                row["connected_at"]
            )

            con.execute(
                """
                UPDATE sessions
                SET
                    disconnected_at = ?,
                    duration = ?
                WHERE id = ?
                """,
                (
                    stamp,
                    max(
                        0,
                        stamp
                        - connected_at,
                    ),
                    row["id"],
                ),
            )


        #
        # Falls uns ein Connect-Event
        # entgangen sein sollte, erzeugen
        # wir aus dem Snapshot trotzdem
        # eine Session.
        #

        for remote_call in clients:

            if remote_call in open_calls:
                continue

            _open_session(
                con,
                remote_call,
                "unknown",
                stamp,
            )

        return


def ingest_events() -> None:

    if not EVENT_LOG.is_file():
        return

    with DB_LOCK:

        with _db() as con:

            try:

                offset = int(
                    _meta_get(
                        con,
                        "event_offset",
                        "0",
                    )
                    or 0
                )

            except ValueError:

                offset = 0


            try:

                file_size = (
                    EVENT_LOG
                    .stat()
                    .st_size
                )

            except OSError:

                return


            #
            # Eventdatei wurde rotiert/
            # geleert.
            #

            if offset > file_size:
                offset = 0


            with EVENT_LOG.open(
                "rb"
            ) as fh:

                fh.seek(
                    offset
                )

                while True:

                    raw = fh.readline()

                    if not raw:
                        break

                    line = (
                        raw.decode(
                            "utf-8",
                            errors="replace",
                        )
                        .rstrip(
                            "\r\n"
                        )
                    )

                    parts = line.split(
                        "\t",
                        3,
                    )

                    if len(parts) < 2:
                        continue

                    try:

                        stamp = int(
                            parts[0]
                        )

                    except ValueError:

                        continue


                    event = (
                        parts[1]
                        if len(parts) > 1
                        else ""
                    )

                    call = (
                        parts[2]
                        if len(parts) > 2
                        else ""
                    )

                    clients = (
                        parts[3]
                        if len(parts) > 3
                        else ""
                    )


                    _process_event(
                        con,
                        stamp,
                        event,
                        call,
                        clients,
                    )


                _meta_set(
                    con,
                    "event_offset",
                    fh.tell(),
                )

            con.commit()


# ============================================================
# CONFIG
# ============================================================

def _config() -> dict[str, str]:

    result: dict[
        str,
        str,
    ] = {}

    if not CONFIG_PATH.is_file():
        return result

    for raw in (
        CONFIG_PATH
        .read_text(
            encoding="utf-8",
            errors="replace",
        )
        .splitlines()
    ):

        line = raw.strip()

        if (
            not line
            or line.startswith("#")
            or line.startswith(";")
            or line.startswith("[")
            or "=" not in line
        ):
            continue

        key, value = line.split(
            "=",
            1,
        )

        result[
            key.strip().upper()
        ] = (
            value.strip()
            .strip('"')
        )

    return result


def _module_id() -> str:
    module_id = (
        _config()
        .get(
            "ID",
            "",
        )
        .strip()
    )

    if not module_id.isdigit():
        raise RuntimeError(
            "Ungültige EchoLink Modul-ID "
            f"in {CONFIG_PATH}: "
            f"{module_id or 'nicht gesetzt'}"
        )

    return module_id


def _node_id() -> str:

    if not NODE_INFO_PATH.is_file():
        return ""

    try:

        data = json.loads(
            NODE_INFO_PATH
            .read_text(
                encoding="utf-8",
            )
        )

    except Exception:
        return ""

    value = (
        data.get("Echolink")
        or data.get("EchoLink")
        or data.get("echolink")
        or ""
    )

    return str(
        value
    ).strip()


# ============================================================
# DIRECTORY STATUS
# ============================================================

def _directory_status() -> str:

    latest = "?"

    try:

        files = [
            item
            for item in Path(
                "/var/log"
            ).glob(
                "svxlink*"
            )
            if item.is_file()
        ]

        files.sort(
            key=lambda item:
                item.stat().st_mtime
        )

    except OSError:

        return latest


    for path in files:

        try:

            size = (
                path.stat()
                .st_size
            )

            with path.open(
                "rb"
            ) as fh:

                fh.seek(
                    max(
                        0,
                        size
                        - 2_000_000,
                    )
                )

                text = (
                    fh.read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

        except OSError:

            continue


        for match in (
            DIRECTORY_RE
            .finditer(
                text
            )
        ):

            latest = (
                match
                .group(1)
                .upper()
            )

    return latest


# ============================================================
# CONTROL
# ============================================================

def _control_state() -> dict[
    str,
    Any,
]:

    available = (
        CONTROL_PTY.exists()
        and os.access(
            CONTROL_PTY,
            os.W_OK,
        )
    )

    return {
        "enabled":
            available,

        "reason":
            (
                "SvxLink Control-PTY "
                "ist schreibbar."
                if available
                else
                "SvxLink Control-PTY "
                "ist für den WebUI-Dienst "
                "nicht schreibbar."
            ),

        "path":
            str(
                CONTROL_PTY
            ),
    }


def _write_dtmf(
    command: str,
) -> None:

    if not re.fullmatch(
        r"[0-9*#]+",
        command,
    ):

        raise ValueError(
            "Ungültiger "
            "SvxLink-DTMF-Befehl."
        )


    if not CONTROL_PTY.exists():

        raise RuntimeError(
            "SvxLink Control-PTY "
            "existiert nicht."
        )


    fd = os.open(
        str(
            CONTROL_PTY
        ),
        os.O_WRONLY
        | os.O_NONBLOCK,
    )

    try:

        data = command.encode(
            "ascii"
        )

        written = os.write(
            fd,
            data,
        )

        if written != len(
            data
        ):

            raise RuntimeError(
                "SvxLink Control-PTY "
                "hat den Befehl nicht "
                "vollständig angenommen."
            )

    finally:

        os.close(
            fd
        )


# ============================================================
# SAVED NODES
# ============================================================

def list_nodes() -> list[
    dict[str, Any]
]:

    with _db() as con:

        rows = con.execute(
            """
            SELECT
                node_id,
                callsign,
                label,
                created_at,
                updated_at
            FROM nodes
            ORDER BY
                label COLLATE NOCASE,
                callsign COLLATE NOCASE
            """
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]


def save_node(
    node_id: str,
    callsign: str,
    label: str = "",
) -> dict[str, Any]:

    node_id = (
        str(node_id or "")
        .strip()
    )

    callsign = (
        str(callsign or "")
        .strip()
        .upper()
    )

    label = (
        str(label or "")
        .strip()
    )


    if not NODE_ID_RE.fullmatch(
        node_id
    ):

        raise ValueError(
            "EchoLink Node-ID muss "
            "numerisch sein."
        )


    if not CALL_RE.fullmatch(
        callsign
    ):

        raise ValueError(
            "Ungültiges EchoLink-"
            "Rufzeichen."
        )


    if not label:
        label = callsign

    label = label[:80]

    now = int(
        time.time()
    )


    with DB_LOCK:

        with _db() as con:

            con.execute(
                """
                INSERT INTO nodes (
                    node_id,
                    callsign,
                    label,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT(node_id)
                DO UPDATE SET
                    callsign =
                        excluded.callsign,
                    label =
                        excluded.label,
                    updated_at =
                        excluded.updated_at
                """,
                (
                    node_id,
                    callsign,
                    label,
                    now,
                    now,
                ),
            )

            con.commit()


    return {
        "saved": True,
        "node_id": node_id,
        "callsign": callsign,
        "label": label,
    }


def delete_node(
    node_id: str,
) -> dict[str, Any]:

    node_id = (
        str(node_id or "")
        .strip()
    )

    with DB_LOCK:

        with _db() as con:

            cur = con.execute(
                """
                DELETE FROM nodes
                WHERE node_id = ?
                """,
                (
                    node_id,
                ),
            )

            con.commit()

    return {
        "deleted":
            cur.rowcount > 0,

        "node_id":
            node_id,
    }


# ============================================================
# SESSION SERIALIZATION
# ============================================================

def _session_dict(
    row: sqlite3.Row,
    now: int,
) -> dict[str, Any]:

    connected_at = int(
        row["connected_at"]
    )

    disconnected_at = (
        int(
            row["disconnected_at"]
        )
        if row[
            "disconnected_at"
        ] is not None
        else None
    )

    duration = (
        int(
            row["duration"]
        )
        if row["duration"]
        is not None
        else max(
            0,
            now - connected_at,
        )
    )

    rf_known = bool(
        row[
            "rf_activity_known"
        ]
    )

    rf_activity = (
        bool(
            row[
                "rf_activity"
            ]
        )
        if rf_known
        else None
    )


    return {
        "id":
            int(
                row["id"]
            ),

        "callsign":
            str(
                row["callsign"]
            ),

        "direction":
            str(
                row["direction"]
            ),

        "connected_at":
            connected_at,

        "connected_at_iso":
            _utc_iso(
                connected_at
            ),

        "disconnected_at":
            disconnected_at,

        "disconnected_at_iso":
            _utc_iso(
                disconnected_at
            ),

        "duration":
            duration,

        #
        # Noch null, bis wir STATE_PTY
        # an den Logger angebunden haben.
        #
        "rf_activity":
            rf_activity,

        "rf_activity_known":
            rf_known,

        "possibly_missed":
            (
                rf_known
                and not rf_activity
                and str(
                    row["direction"]
                )
                == "incoming"
            ),
    }


# ============================================================
# STATUS / HISTORY
# ============================================================

def history(
    limit: int = 50,
) -> list[
    dict[str, Any]
]:

    ingest_events()

    limit = max(
        1,
        min(
            int(limit),
            200,
        ),
    )

    now = int(
        time.time()
    )

    with _db() as con:

        rows = con.execute(
            """
            SELECT *
            FROM sessions
            WHERE disconnected_at
                  IS NOT NULL
            ORDER BY connected_at DESC
            LIMIT ?
            """,
            (
                limit,
            ),
        ).fetchall()

    return [
        _session_dict(
            row,
            now,
        )
        for row in rows
    ]


def status(
    history_limit: int = 30,
) -> dict[str, Any]:

    ingest_events()

    cfg = _config()

    now = int(
        time.time()
    )

    with _db() as con:

        module_active = (
            _meta_get(
                con,
                "module_active",
                "0",
            )
            == "1"
        )

        pending = _meta_get(
            con,
            "pending_outgoing",
            "",
        )

        open_rows = con.execute(
            """
            SELECT *
            FROM sessions
            WHERE disconnected_at
                  IS NULL
            ORDER BY connected_at ASC
            """
        ).fetchall()


    clients = [
        _session_dict(
            row,
            now,
        )
        for row in open_rows
    ]


    if clients:
        module_active = True


    directory_status = (
        _directory_status()
    )


    return {
        "callsign":
            cfg.get(
                "CALLSIGN",
                "",
            ),

        "node_id":
            _node_id(),

        "module_id":
            cfg.get(
                "ID",
                "",
            ),

        "directory_status":
            directory_status,

        "directory_online":
            directory_status
            == "ON",

        "module_active":
            module_active,

        "pending_outgoing":
            pending or None,

        "client_count":
            len(
                clients
            ),

        "clients":
            clients,

        "nodes":
            list_nodes(),

        "history":
            (
                history(
                    history_limit
                )
                if history_limit > 0
                else []
            ),

        "control":
            _control_state(),

        "event_log":
            {
                "available":
                    EVENT_LOG.is_file(),

                "path":
                    str(
                        EVENT_LOG
                    ),
            },
    }


# ============================================================
# CONTROL ACTIONS
# ============================================================

def activate_module() -> dict[
    str,
    Any,
]:

    ingest_events()

    current = status(
        history_limit=0,
    )

    if current[
        "module_active"
    ]:

        return {
            "accepted": True,
            "already_active":
                True,
            "confirmed":
                True,
        }


    _write_dtmf(
        f"{_module_id()}#"
    )

    return {
        "accepted": True,
        "already_active":
            False,
        "confirmed":
            False,
        "command":
            "activate",
    }


def deactivate_module() -> dict[
    str,
    Any,
]:

    #
    # EchoLink-Modul:
    #
    # # = bestehende Verbindung
    #     beenden
    #
    # Ein weiterer # verlässt danach
    # das Modul.
    #

    _write_dtmf(
        "#"
    )

    time.sleep(
        0.35
    )

    _write_dtmf(
        "#"
    )

    return {
        "accepted": True,
        "confirmed": False,
        "command":
            "deactivate",
    }


def connect_node(
    node_id: str,
) -> dict[
    str,
    Any,
]:

    node_id = (
        str(node_id or "")
        .strip()
    )


    if not NODE_ID_RE.fullmatch(
        node_id
    ):

        raise ValueError(
            "Ungültige EchoLink "
            "Node-ID."
        )


    ingest_events()

    current = status(
        history_limit=0,
    )


    #
    # Modul zuerst aktivieren.
    #

    if not current[
        "module_active"
    ]:

        _write_dtmf(
            f"{_module_id()}#"
        )

        time.sleep(
            0.50
        )


    #
    # Im EchoLink-Modul wird die
    # Node-ID direkt gewählt.
    #

    _write_dtmf(
        f"{node_id}#"
    )


    return {
        "accepted": True,
        "confirmed": False,
        "node_id":
            node_id,
    }


def disconnect() -> dict[
    str,
    Any,
]:

    _write_dtmf(
        "#"
    )

    return {
        "accepted": True,
        "confirmed": False,
        "command":
            "disconnect",
    }


_init_db()


# ============================================================
# ECHOLINK DIRECTORY SEARCH V2
#
# Official sources:
#
# https://www.echolink.org/validation/node_lookup.jsp
# https://www.echolink.org/logins.jsp
#
# HTML parsing is intentionally isolated here so the
# provider can later be replaced without changing the API.
# ============================================================

from html.parser import HTMLParser
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.parse import (
    urlencode,
    urljoin,
)
from urllib.request import (
    Request,
    urlopen,
)


ECHOLINK_LOOKUP_URL = (
    "https://www.echolink.org/"
    "validation/node_lookup.jsp"
)

ECHOLINK_LOGINS_URL = (
    "https://www.echolink.org/"
    "logins.jsp"
)

ECHOLINK_HTTP_TIMEOUT = 5

_ECHOLINK_HTTP_HEADERS = {
    "User-Agent":
        "SvxLink-WebUI/1.0",

    "Accept":
        "text/html,"
        "application/xhtml+xml",
}

_DIRECTORY_CACHE_LOCK = (
    threading.RLock()
)

_DIRECTORY_CACHE = {
    "timestamp": 0.0,
    "stations": [],
    "error": None,
}


class _EchoTablesParser(
    HTMLParser
):

    def __init__(self):
        super().__init__()

        self.rows = []

        self._row = None
        self._cell = None


    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        tag = tag.lower()

        if tag == "tr":

            self._row = []


        elif (
            tag in (
                "td",
                "th",
            )
            and self._row
            is not None
        ):

            self._cell = []


    def handle_data(
        self,
        data,
    ):

        if self._cell is not None:

            self._cell.append(
                data
            )


    def handle_endtag(
        self,
        tag,
    ):

        tag = tag.lower()

        if (
            tag in (
                "td",
                "th",
            )
            and self._cell
            is not None
        ):

            value = re.sub(
                r"\s+",
                " ",
                "".join(
                    self._cell
                ),
            ).strip()

            self._row.append(
                value
            )

            self._cell = None


        elif (
            tag == "tr"
            and self._row
            is not None
        ):

            if self._row:

                self.rows.append(
                    self._row
                )

            self._row = None
            self._cell = None


class _EchoFormParser(
    HTMLParser
):

    def __init__(self):
        super().__init__()

        self.forms = []
        self.current = None


    def handle_starttag(
        self,
        tag,
        attrs,
    ):

        tag = tag.lower()

        attrs = dict(
            attrs
        )


        if tag == "form":

            self.current = {
                "action":
                    attrs.get(
                        "action",
                        "",
                    ),

                "method":
                    attrs.get(
                        "method",
                        "GET",
                    ).upper(),

                "inputs":
                    [],
            }

            return


        if (
            tag == "input"
            and self.current
            is not None
        ):

            self.current[
                "inputs"
            ].append(
                attrs
            )


    def handle_endtag(
        self,
        tag,
    ):

        if (
            tag.lower()
            == "form"
            and self.current
            is not None
        ):

            self.forms.append(
                self.current
            )

            self.current = None


class _EchoTextParser(
    HTMLParser
):

    def __init__(self):
        super().__init__()

        self.parts = []


    def handle_data(
        self,
        data,
    ):

        value = re.sub(
            r"\s+",
            " ",
            data,
        ).strip()

        if value:

            self.parts.append(
                value
            )


def _echolink_http(
    url: str,
    *,
    data: dict | None = None,
    method: str = "GET",
) -> str:

    method = (
        method.upper()
    )

    encoded = None


    if data is not None:

        if method == "GET":

            query = urlencode(
                data
            )

            separator = (
                "&"
                if "?" in url
                else "?"
            )

            url = (
                url
                + separator
                + query
            )

        else:

            encoded = urlencode(
                data
            ).encode(
                "utf-8"
            )


    request = Request(
        url,
        data=encoded,
        headers=
            _ECHOLINK_HTTP_HEADERS,
        method=method,
    )


    with urlopen(
        request,
        timeout=
            ECHOLINK_HTTP_TIMEOUT,
    ) as response:

        raw = response.read(
            8 * 1024 * 1024
        )


    return raw.decode(
        "utf-8",
        errors="replace",
    )


def _parse_current_logins(
    html: str,
) -> list[dict[str, Any]]:

    parser = (
        _EchoTablesParser()
    )

    parser.feed(
        html
    )


    stations = []

    seen = set()


    for row in parser.rows:

        if len(row) < 3:
            continue


        status_index = None

        for index, cell in enumerate(
            row
        ):

            upper = (
                cell.strip()
                .upper()
            )

            if upper in (
                "ON",
                "BUSY",
            ):

                status_index = index
                break


        if status_index is None:
            continue


        node_id = None
        node_index = None

        for index in range(
            len(row) - 1,
            -1,
            -1,
        ):

            value = (
                row[index]
                .strip()
            )

            if re.fullmatch(
                r"\d{1,9}",
                value,
            ):

                node_id = value
                node_index = index
                break


        if not node_id:
            continue


        callsign = (
            row[0]
            .strip()
            .upper()
        )


        if not re.fullmatch(
            r"(?:"
            r"[A-Z0-9/]{2,16}"
            r"(?:-[LR])?"
            r"|"
            r"\*[A-Z0-9_-]+\*"
            r")",
            callsign,
        ):

            continue


        key = (
            callsign,
            node_id,
        )

        if key in seen:
            continue

        seen.add(
            key
        )


        location_parts = []

        for index, value in enumerate(
            row
        ):

            if index == 0:
                continue

            if index == status_index:
                continue

            if index == node_index:
                continue

            if re.fullmatch(
                r"\d{1,2}:\d{2}",
                value.strip(),
            ):
                continue

            if value.strip():

                location_parts.append(
                    value.strip()
                )


        stations.append({
            "callsign":
                callsign,

            "node_id":
                node_id,

            "status":
                row[
                    status_index
                ].strip().lower(),

            "online":
                True,

            "location":
                " ".join(
                    location_parts
                ).strip(),

            "source":
                "echolink-current-logins",
        })


    return stations


def _current_logins(
    force: bool = False,
) -> list[dict[str, Any]]:

    now = time.time()


    with _DIRECTORY_CACHE_LOCK:

        age = (
            now
            - float(
                _DIRECTORY_CACHE[
                    "timestamp"
                ]
                or 0
            )
        )


        if (
            not force
            and _DIRECTORY_CACHE[
                "stations"
            ]
            and age < 60
        ):

            return list(
                _DIRECTORY_CACHE[
                    "stations"
                ]
            )


        try:

            html = _echolink_http(
                ECHOLINK_LOGINS_URL
            )

            stations = (
                _parse_current_logins(
                    html
                )
            )


            _DIRECTORY_CACHE.update({
                "timestamp":
                    now,

                "stations":
                    stations,

                "error":
                    None,
            })


            return list(
                stations
            )


        except Exception as exc:

            #
            # Stale Daten sind besser
            # als alle 2 Sekunden ein
            # blockierender Retry.
            #

            stale = list(
                _DIRECTORY_CACHE[
                    "stations"
                ]
            )

            _DIRECTORY_CACHE.update({
                "timestamp":
                    now,

                "error":
                    str(exc),
            })

            return stale


def _lookup_form_request(
    query: str,
) -> str:

    html = _echolink_http(
        ECHOLINK_LOOKUP_URL
    )


    parser = (
        _EchoFormParser()
    )

    parser.feed(
        html
    )


    chosen = None
    query_input = None


    for form in parser.forms:

        for item in form[
            "inputs"
        ]:

            input_type = (
                item.get(
                    "type",
                    "text",
                )
                .lower()
            )

            name = item.get(
                "name"
            )


            if (
                name
                and input_type
                in (
                    "text",
                    "search",
                    "number",
                )
            ):

                chosen = form
                query_input = item
                break


        if chosen:
            break


    if (
        not chosen
        or not query_input
    ):

        raise RuntimeError(
            "EchoLink Lookup-Formular "
            "konnte nicht erkannt werden."
        )


    payload = {}


    for item in chosen[
        "inputs"
    ]:

        name = item.get(
            "name"
        )

        if not name:
            continue


        input_type = (
            item.get(
                "type",
                "text",
            )
            .lower()
        )


        if input_type == "hidden":

            payload[name] = (
                item.get(
                    "value",
                    "",
                )
            )


        elif input_type in (
            "submit",
            "button",
        ):

            value = item.get(
                "value"
            )

            if value:

                payload[name] = value


    payload[
        query_input["name"]
    ] = query


    action = (
        chosen.get(
            "action"
        )
        or ECHOLINK_LOOKUP_URL
    )

    url = urljoin(
        ECHOLINK_LOOKUP_URL,
        action,
    )


    return _echolink_http(
        url,
        data=payload,
        method=chosen.get(
            "method",
            "GET",
        ),
    )


def _parse_lookup_result(
    html: str,
    query: str,
) -> list[dict[str, Any]]:

    query = (
        str(query or "")
        .strip()
        .upper()
    )


    table = (
        _EchoTablesParser()
    )

    table.feed(
        html
    )


    results = []
    seen = set()


    def add(
        callsign: str,
        node_id: str,
    ):

        callsign = (
            callsign
            .strip()
            .upper()
        )

        node_id = (
            node_id
            .strip()
        )


        if (
            not re.fullmatch(
                r"(?:"
                r"[A-Z0-9/]{2,16}"
                r"(?:-[LR])?"
                r"|"
                r"\*[A-Z0-9_-]+\*"
                r")",
                callsign,
            )
            or (
                not callsign.startswith("*")
                and not re.search(
                    r"[A-Z]",
                    callsign,
                )
            )
        ):
            return


        if not re.fullmatch(
            r"\d{1,9}",
            node_id,
        ):
            return


        key = (
            callsign,
            node_id,
        )

        if key in seen:
            return

        seen.add(
            key
        )


        results.append({
            "callsign":
                callsign,

            "node_id":
                node_id,

            "status":
                "offline",

            "online":
                False,

            "location":
                "",

            "exists":
                True,

            "source":
                "echolink-node-lookup",
        })


    for row in table.rows:

        calls = []

        numbers = []


        for value in row:

            candidate = (
                value.strip()
                .upper()
            )


            if re.fullmatch(
                r"(?:"
                r"[A-Z0-9/]{2,16}"
                r"(?:-[LR])?"
                r"|"
                r"\*[A-Z0-9_-]+\*"
                r")",
                candidate,
            ):

                calls.append(
                    candidate
                )


            if re.fullmatch(
                r"\d{1,9}",
                value.strip(),
            ):

                numbers.append(
                    value.strip()
                )


        if not calls or not numbers:
            continue


        row_text = (
            " ".join(
                row
            ).upper()
        )


        if (
            query not in row_text
            and not any(
                call == query
                for call in calls
            )
            and not any(
                node == query
                for node in numbers
            )
        ):
            continue


        for call in calls:

            for node in numbers:

                add(
                    call,
                    node,
                )


    #
    # Fallback für Seiten ohne Tabellenlayout.
    #

    if not results:

        text_parser = (
            _EchoTextParser()
        )

        text_parser.feed(
            html
        )

        text = " ".join(
            text_parser.parts
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )


        patterns = [
            re.compile(
                r"(?:Callsign|Call Sign)"
                r"\s*:?\s*"
                r"([A-Z0-9/]+(?:-[LR])?)"
                r".{0,120}?"
                r"(?:Node(?: Number| ID)?)"
                r"\s*:?\s*(\d{1,9})",
                re.I,
            ),

            re.compile(
                r"(?:Node(?: Number| ID)?)"
                r"\s*:?\s*(\d{1,9})"
                r".{0,120}?"
                r"(?:Callsign|Call Sign)"
                r"\s*:?\s*"
                r"([A-Z0-9/]+(?:-[LR])?)",
                re.I,
            ),
        ]


        for index, pattern in enumerate(
            patterns
        ):

            for match in pattern.finditer(
                text
            ):

                if index == 0:

                    add(
                        match.group(1),
                        match.group(2),
                    )

                else:

                    add(
                        match.group(2),
                        match.group(1),
                    )


    return results


def _registered_lookup(
    query: str,
) -> list[dict[str, Any]]:

    try:

        html = (
            _lookup_form_request(
                query
            )
        )

        return (
            _parse_lookup_result(
                html,
                query,
            )
        )

    except Exception:

        return []


def directory_search(
    query: str,
) -> dict[str, Any]:

    query = (
        str(query or "")
        .strip()
        .upper()
    )


    if not query:

        raise ValueError(
            "Bitte Rufzeichen oder "
            "Node-ID eingeben."
        )


    if len(query) > 32:

        raise ValueError(
            "Suchbegriff ist zu lang."
        )


    if not re.fullmatch(
        r"[A-Z0-9/*_-]+",
        query,
    ):

        raise ValueError(
            "Ungültiger Suchbegriff."
        )


    online_stations = (
        _current_logins()
    )


    online_by_call = {
        item["callsign"]:
            item
        for item in online_stations
    }

    online_by_node = {
        item["node_id"]:
            item
        for item in online_stations
    }


    results = {}



    def merge(
        item: dict[str, Any],
    ):

        key = (
            item.get(
                "node_id",
                "",
            )
            or item.get(
                "callsign",
                "",
            )
        )

        if not key:
            return


        current = (
            results.get(
                key,
                {}
            )
        )

        current.update(
            item
        )


        live = None

        node_id = str(
            current.get(
                "node_id",
                "",
            )
        )

        callsign = str(
            current.get(
                "callsign",
                "",
            )
        ).upper()


        if node_id:

            live = (
                online_by_node.get(
                    node_id
                )
            )


        if (
            live is None
            and callsign
        ):

            live = (
                online_by_call.get(
                    callsign
                )
            )


        if live:

            current.update(
                live
            )

            current[
                "exists"
            ] = True

        else:

            current.setdefault(
                "status",
                "offline",
            )

            current.setdefault(
                "online",
                False,
            )

            current.setdefault(
                "exists",
                True,
            )


        results[key] = current


    #
    # Aktuell eingeloggte Stationen
    # zuerst erfassen.
    #

    if query.isdigit():

        live = (
            online_by_node.get(
                query
            )
        )

        if live:

            merge(
                live
            )

    else:

        for item in online_stations:

            call = (
                item["callsign"]
                .upper()
            )


            if (
                call == query
                or call.startswith(
                    query + "-"
                )
            ):

                merge(
                    item
                )


    #
    # Registrierte Node nachschlagen.
    #
    # Bei einem Basisrufzeichen probieren
    # wir zusätzlich -L und -R.
    #

    lookup_queries = [
        query
    ]


    if (
        not query.isdigit()
        and not query.endswith(
            (
                "-L",
                "-R",
            )
        )
    ):

        lookup_queries.extend([
            f"{query}-L",
            f"{query}-R",
        ])


    for lookup_query in lookup_queries:

        for item in (
            _registered_lookup(
                lookup_query
            )
        ):

            merge(
                item
            )


    result_list = list(
        results.values()
    )


    result_list.sort(
        key=lambda item: (
            0
            if item.get(
                "status"
            ) == "on"
            else
            1
            if item.get(
                "status"
            ) == "busy"
            else
            2,

            item.get(
                "callsign",
                "",
            ),
        )
    )


    return {
        "query":
            query,

        "count":
            len(
                result_list
            ),

        "results":
            result_list,

        "directory_cache_age":
            max(
                0,
                int(
                    time.time()
                    - float(
                        _DIRECTORY_CACHE[
                            "timestamp"
                        ]
                        or 0
                    )
                ),
            ),

        "directory_error":
            _DIRECTORY_CACHE[
                "error"
            ],
    }


#
# Existing list_nodes() is intentionally wrapped
# so saved favourites also get current status.
#

_list_nodes_database_v2 = (
    list_nodes
)


def list_nodes() -> list[
    dict[str, Any]
]:

    nodes = (
        _list_nodes_database_v2()
    )

    if not nodes:
        return []


    stations = (
        _current_logins()
    )


    by_node = {
        item["node_id"]:
            item
        for item in stations
    }

    by_call = {
        item["callsign"]:
            item
        for item in stations
    }


    enriched = []


    for node in nodes:

        item = dict(
            node
        )

        live = (
            by_node.get(
                str(
                    node.get(
                        "node_id",
                        "",
                    )
                )
            )
        )


        if live is None:

            live = (
                by_call.get(
                    str(
                        node.get(
                            "callsign",
                            "",
                        )
                    ).upper()
                )
            )


        if live:

            item.update({
                "status":
                    live.get(
                        "status",
                        "on",
                    ),

                "online":
                    True,

                "location":
                    live.get(
                        "location",
                        "",
                    ),
            })

        else:

            item.update({
                "status":
                    "offline",

                "online":
                    False,

                "location":
                    "",
            })


        enriched.append(
            item
        )


    return enriched


# ECHOLINK DIRECTORY SEARCH V2

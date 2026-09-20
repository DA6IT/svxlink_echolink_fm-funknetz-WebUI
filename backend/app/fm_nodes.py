from __future__ import annotations

import json
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import paho.mqtt.client as mqtt


class FMNodeDirectory:
    """
    Read-only directory of FM-Funknetz nodes.

    Sources:
      reflector*.json       known node metadata
      */nodes_index         current online presence
      */nodes/<CALL>        retained/live node state

    No MQTT messages are ever published.
    """

    def __init__(
        self,
        host: str,
        port: int,
        bases: tuple[
            tuple[str, str],
            ...
        ],
        snapshots: tuple[
            tuple[str, str],
            ...
        ],
    ) -> None:
        self.host = host
        self.port = port
        self.bases = bases
        self.snapshots = snapshots

        self._lock = (
            threading.RLock()
        )

        self._client: (
            mqtt.Client | None
        ) = None

        self._connected = False

        self._nodes: dict[
            str,
            dict[str, Any],
        ] = {}

        self._online_by_server: dict[
            str,
            set[str],
        ] = {}

        self._have_index: set[
            str
        ] = set()

        self._updated_at: (
            str | None
        ) = None

    @staticmethod
    def _normalize_call(
        value: Any,
    ) -> str:
        return (
            str(value or "")
            .strip()
            .upper()
        )

    @staticmethod
    def belongs_to_base(
        call: str,
        base: str,
    ) -> bool:
        call = (
            str(call)
            .strip()
            .upper()
        )

        base = (
            str(base)
            .strip()
            .upper()
        )

        if (
            not call
            or not base
        ):
            return False

        return (
            call == base
            or call.startswith(
                base + "-"
            )
            or call.startswith(
                base + "/"
            )
            or call.endswith(
                "/" + base
            )
            or (
                "/" + base + "-"
            ) in call
            or (
                "/" + base + "/"
            ) in call
        )

    @staticmethod
    def _scalar(
        value: Any,
    ) -> Any:
        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value

        return None

    @classmethod
    def _find_value(
        cls,
        raw: dict[str, Any],
        names: tuple[str, ...],
    ) -> Any:
        wanted = {
            item.lower()
            for item in names
        }

        queue: list[Any] = [
            raw
        ]

        depth = 0

        while (
            queue
            and depth < 250
        ):
            depth += 1

            item = queue.pop(
                0
            )

            if not isinstance(
                item,
                dict,
            ):
                continue

            for key, value in (
                item.items()
            ):
                normalized = (
                    str(key)
                    .replace(
                        "-",
                        "_",
                    )
                    .lower()
                )

                if (
                    normalized
                    in wanted
                ):
                    if (
                        value is not None
                        and value != ""
                    ):
                        return value

                if isinstance(
                    value,
                    dict,
                ):
                    queue.append(
                        value
                    )

        return None

    @classmethod
    def _tg(
        cls,
        raw: dict[str, Any],
    ) -> str:
        value = cls._find_value(
            raw,
            (
                "tg",
                "talkgroup",
                "talk_group",
                "currenttg",
                "current_tg",
                "selectedtg",
                "selected_tg",
            ),
        )

        if value is None:
            return ""

        return str(
            value
        ).strip()

    @classmethod
    def _location(
        cls,
        raw: dict[str, Any],
    ) -> str:
        value = cls._find_value(
            raw,
            (
                "location",
                "qth",
                "loc",
                "place",
                "city",
            ),
        )

        scalar = cls._scalar(
            value
        )

        return (
            str(scalar)
            if scalar is not None
            else ""
        )

    @classmethod
    def _sysop(
        cls,
        raw: dict[str, Any],
    ) -> str:
        value = cls._find_value(
            raw,
            (
                "sysop",
                "operator",
                "op",
                "name",
            ),
        )

        scalar = cls._scalar(
            value
        )

        return (
            str(scalar)
            if scalar is not None
            else ""
        )

    @classmethod
    def _monitored(
        cls,
        raw: dict[str, Any],
    ) -> list[str]:
        value = cls._find_value(
            raw,
            (
                "monitoredtgs",
                "monitored_tgs",
                "monitor_tgs",
                "monitor",
                "monitored",
            ),
        )

        if isinstance(
            value,
            list,
        ):
            return [
                str(item)
                for item in value
                if str(
                    item
                ).strip()
            ]

        if isinstance(
            value,
            str,
        ):
            return [
                part.strip()
                for part
                in value.replace(
                    ";",
                    ",",
                ).split(",")
                if part.strip()
            ]

        return []

    @classmethod
    def _node_last_seen(
        cls,
        raw: dict[str, Any],
    ) -> Any:
        value = cls._find_value(
            raw,
            (
                "lastseen",
                "last_seen",
                "seen",
                "timestamp",
                "ts",
            ),
        )

        return cls._scalar(
            value
        )

    def _ensure_node(
        self,
        call: str,
    ) -> dict[str, Any]:
        call = (
            self._normalize_call(
                call
            )
        )

        node = (
            self._nodes.get(
                call
            )
        )

        if node is None:
            node = {
                "call":
                    call,

                "raw":
                    {},

                "known_servers":
                    set(),
            }

            self._nodes[
                call
            ] = node

        return node

    def _merge_raw(
        self,
        node: dict[str, Any],
        incoming: dict[str, Any],
    ) -> None:
        raw = node.setdefault(
            "raw",
            {},
        )

        nested_raw = (
            incoming.get(
                "raw"
            )
        )

        if isinstance(
            nested_raw,
            dict,
        ):
            raw.update(
                nested_raw
            )

        for key, value in (
            incoming.items()
        ):
            if key == "raw":
                continue

            raw[
                key
            ] = value

    def _load_snapshot(
        self,
        server: str,
        url: str,
    ) -> None:
        request = (
            urllib.request.Request(
                url,
                headers={
                    "User-Agent":
                        "svxlink-webui/0.5"
                },
            )
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=6,
            ) as response:
                data = json.loads(
                    response.read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

        except Exception:
            return

        nodes = (
            data.get(
                "nodes",
                {},
            )
            if isinstance(
                data,
                dict,
            )
            else {}
        )

        if not isinstance(
            nodes,
            dict,
        ):
            return

        with self._lock:
            for call, raw in (
                nodes.items()
            ):
                call = (
                    self._normalize_call(
                        call
                    )
                )

                if not call:
                    continue

                node = (
                    self._ensure_node(
                        call
                    )
                )

                node[
                    "known_servers"
                ].add(
                    str(server)
                )

                if isinstance(
                    raw,
                    dict,
                ):
                    self._merge_raw(
                        node,
                        raw,
                    )

            self._updated_at = (
                datetime.now()
                .astimezone()
                .isoformat()
            )

    def _load_snapshots(
        self,
    ) -> None:
        with ThreadPoolExecutor(
            max_workers=2
        ) as pool:
            futures = [
                pool.submit(
                    self._load_snapshot,
                    server,
                    url,
                )
                for server, url
                in self.snapshots
            ]

            for future in futures:
                try:
                    future.result()
                except Exception:
                    pass

    def start(
        self,
    ) -> None:
        if (
            self._client
            is not None
        ):
            return

        #
        # Zwei kleine Dateien parallel
        # einlesen, damit die Suche sofort
        # auch Offline-Nodes kennt.
        #
        self._load_snapshots()

        client = mqtt.Client(
            callback_api_version=
                mqtt.CallbackAPIVersion.VERSION2,
            client_id=
                "svxlink-webui-nodes",
            protocol=
                mqtt.MQTTv311,
        )

        client.enable_logger()

        client.reconnect_delay_set(
            min_delay=1,
            max_delay=30,
        )

        client.on_connect = (
            self._handle_connect
        )

        client.on_disconnect = (
            self._handle_disconnect
        )

        client.on_message = (
            self._handle_message
        )

        self._client = client

        client.connect_async(
            self.host,
            self.port,
            keepalive=30,
        )

        client.loop_start()

    def stop(
        self,
    ) -> None:
        client = self._client

        self._client = None

        if client is None:
            return

        try:
            client.disconnect()
        finally:
            client.loop_stop()

        with self._lock:
            self._connected = False

    def _handle_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ) -> None:
        is_failure = getattr(
            reason_code,
            "is_failure",
            None,
        )

        if is_failure is None:
            ok = (
                reason_code == 0
            )
        else:
            ok = (
                not is_failure
            )

        with self._lock:
            self._connected = (
                ok
            )

        if ok:
            for (
                server,
                base,
            ) in self.bases:
                client.subscribe(
                    (
                        base
                        + "/nodes_index"
                    ),
                    qos=0,
                )

                client.subscribe(
                    (
                        base
                        + "/nodes/+"
                    ),
                    qos=0,
                )

    def _handle_disconnect(
        self,
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ) -> None:
        with self._lock:
            self._connected = False

    def _parse_index(
        self,
        payload: str,
    ) -> set[str]:
        try:
            data = json.loads(
                payload
            )
        except (
            json.JSONDecodeError
        ):
            return set()

        if isinstance(
            data,
            list,
        ):
            source = data

        elif (
            isinstance(
                data,
                dict,
            )
            and isinstance(
                data.get(
                    "nodes"
                ),
                list,
            )
        ):
            source = (
                data["nodes"]
            )

        elif isinstance(
            data,
            dict,
        ):
            source = list(
                data.keys()
            )

        else:
            return set()

        result: set[str] = (
            set()
        )

        for item in source:
            if isinstance(
                item,
                dict,
            ):
                call = (
                    item.get(
                        "call",
                        "",
                    )
                )
            else:
                call = item

            call = (
                self._normalize_call(
                    call
                )
            )

            if call:
                result.add(
                    call
                )

        return result

    def _handle_message(
        self,
        client,
        userdata,
        message,
    ) -> None:
        topic = str(
            message.topic
        )

        payload = (
            message.payload
            .decode(
                "utf-8",
                errors="replace",
            )
            .strip()
        )

        for (
            server,
            base,
        ) in self.bases:
            index_topic = (
                base
                + "/nodes_index"
            )

            if (
                topic
                == index_topic
            ):
                calls = (
                    self._parse_index(
                        payload
                    )
                )

                with self._lock:
                    self._online_by_server[
                        str(server)
                    ] = calls

                    self._have_index.add(
                        str(server)
                    )

                    for call in calls:
                        node = (
                            self._ensure_node(
                                call
                            )
                        )

                        node[
                            "known_servers"
                        ].add(
                            str(server)
                        )

                    self._updated_at = (
                        datetime.now()
                        .astimezone()
                        .isoformat()
                    )

                return

            prefix = (
                base
                + "/nodes/"
            )

            if topic.startswith(
                prefix
            ):
                call = (
                    topic[
                        len(prefix):
                    ]
                    .replace(
                        "/",
                        "",
                    )
                    .strip()
                    .upper()
                )

                if not call:
                    return

                try:
                    obj = (
                        json.loads(
                            payload
                        )
                    )
                except (
                    json.JSONDecodeError
                ):
                    return

                if not isinstance(
                    obj,
                    dict,
                ):
                    return

                with self._lock:
                    node = (
                        self._ensure_node(
                            call
                        )
                    )

                    node[
                        "known_servers"
                    ].add(
                        str(server)
                    )

                    self._merge_raw(
                        node,
                        obj,
                    )

                    node[
                        "mqtt_received_at"
                    ] = (
                        datetime.now()
                        .astimezone()
                        .isoformat()
                    )

                    self._updated_at = (
                        node[
                            "mqtt_received_at"
                        ]
                    )

                return

    def _servers_online(
        self,
        call: str,
    ) -> list[str]:
        return [
            server
            for server, calls
            in self._online_by_server.items()
            if call in calls
        ]

    def _record_locked(
        self,
        call: str,
    ) -> dict[str, Any] | None:
        node = self._nodes.get(
            call
        )

        if node is None:
            return None

        raw = node.get(
            "raw",
            {},
        )

        if not isinstance(
            raw,
            dict,
        ):
            raw = {}

        online_servers = (
            self._servers_online(
                call
            )
        )

        known_servers = sorted(
            str(item)
            for item
            in node.get(
                "known_servers",
                set(),
            )
        )

        return {
            "call":
                call,

            "online":
                bool(
                    online_servers
                ),

            "online_servers":
                online_servers,

            "known_servers":
                known_servers,

            "tg":
                self._tg(
                    raw
                ),

            "monitored_tgs":
                self._monitored(
                    raw
                ),

            "location":
                self._location(
                    raw
                ),

            "sysop":
                self._sysop(
                    raw
                ),

            "node_last_seen":
                self._node_last_seen(
                    raw
                ),

            "mqtt_received_at":
                node.get(
                    "mqtt_received_at"
                ),
        }

    def search(
        self,
        query: str,
    ) -> dict[str, Any]:
        base = (
            self._normalize_call(
                query
            )
        )

        if not base:
            return {
                "query": "",
                "base_call": "",
                "connected": self._connected,
                "nodes": [],
            }

        with self._lock:
            calls = [
                call
                for call
                in self._nodes
                if self.belongs_to_base(
                    call,
                    base,
                )
            ]

            records = [
                self._record_locked(
                    call
                )
                for call in calls
            ]

        records = [
            item
            for item in records
            if item is not None
        ]

        records.sort(
            key=lambda item: (
                0
                if item["call"]
                == base
                else 1,

                0
                if item["online"]
                else 1,

                item["call"],
            )
        )

        return {
            "query":
                query,

            "base_call":
                base,

            "connected":
                self._connected,

            "have_index":
                sorted(
                    self._have_index
                ),

            "updated_at":
                self._updated_at,

            "nodes":
                records,
        }

    def status(
        self,
    ) -> dict[str, Any]:
        with self._lock:
            online = set()

            for calls in (
                self._online_by_server
                .values()
            ):
                online.update(
                    calls
                )

            return {
                "connected":
                    self._connected,

                "known_nodes":
                    len(
                        self._nodes
                    ),

                "online_nodes":
                    len(
                        online
                    ),

                "have_index":
                    sorted(
                        self._have_index
                    ),

                "updated_at":
                    self._updated_at,
            }

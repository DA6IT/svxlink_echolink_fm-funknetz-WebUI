from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Any, Callable

import paho.mqtt.client as mqtt

from .activity_store import ActivityStore


class FMFunknetzMQTT:
    """
    Read-only FM-Funknetz MQTT subscriber.

    Es wird ausschließlich subscribed.
    Dieser Adapter published niemals etwas zum öffentlichen Broker.
    """

    def __init__(
        self,
        host: str,
        port: int,
        topics: tuple[str, ...],
        stale_after: int = 120,
        activity_store: ActivityStore | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.topics = topics
        self.stale_after = stale_after
        self.activity_store = (
            activity_store
        )

        self._lock = (
            threading.RLock()
        )

        self._client: (
            mqtt.Client | None
        ) = None

        self._on_update: (
            Callable[
                [dict[str, Any]],
                None,
            ]
            | None
        ) = None

        self._connected = False

        self._active: dict[
            str,
            dict[str, Any],
        ] = {}

        self._client_count: (
            int | None
        ) = None

        self._updated_at: (
            str | None
        ) = None

        self._last_event: (
            dict[str, Any]
            | None
        ) = None

    def start(
        self,
        on_update: Callable[
            [dict[str, Any]],
            None,
        ]
        | None = None,
    ) -> None:
        if (
            self._client
            is not None
        ):
            return

        self._on_update = (
            on_update
        )

        client = mqtt.Client(
            callback_api_version=
                mqtt.CallbackAPIVersion.VERSION2,
            client_id=
                "svxlink-webui",
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
            ok = not is_failure

        with self._lock:
            self._connected = ok

            self._updated_at = (
                datetime.now()
                .astimezone()
                .isoformat()
            )

        if ok:
            for topic in (
                self.topics
            ):
                client.subscribe(
                    topic,
                    qos=0,
                )

        self._notify()

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

            self._updated_at = (
                datetime.now()
                .astimezone()
                .isoformat()
            )

        self._notify()

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

        changed = False

        if topic.startswith(
            "/server/statethr"
        ):
            try:
                event = (
                    json.loads(
                        payload
                    )
                )
            except (
                json.JSONDecodeError
            ):
                return

            if not isinstance(
                event,
                dict,
            ):
                return

            talk = str(
                event.get(
                    "talk",
                    "",
                )
            ).lower()

            tg = str(
                event.get(
                    "tg",
                    "",
                )
            ).strip()

            call = str(
                event.get(
                    "call",
                    "",
                )
            ).strip().upper()

            if (
                not tg.isdigit()
                or not call
                or call.lower()
                == "welcome"
                or talk not in {
                    "start",
                    "stop",
                }
            ):
                return

            now = time.time()

            received_at = (
                datetime.now()
                .astimezone()
                .isoformat()
            )

            normalized = {
                "call":
                    call,

                "tg":
                    tg,

                "server":
                    str(
                        event.get(
                            "server",
                            "",
                        )
                    ),

                "time":
                    str(
                        event.get(
                            "time",
                            "",
                        )
                    ),

                "talk":
                    talk,

                "received_at":
                    received_at,

                "received_at_epoch":
                    now,

                "_seen":
                    now,
            }

            if (
                self.activity_store
                is not None
            ):
                try:
                    self.activity_store.record_event(
                        normalized
                    )
                except Exception:
                    # Die History darf
                    # niemals den MQTT-
                    # Livestream stoppen.
                    pass

            with self._lock:
                if talk == "start":
                    self._active[
                        tg
                    ] = normalized

                elif talk == "stop":
                    current = (
                        self._active.get(
                            tg
                        )
                    )

                    if (
                        current
                        and current.get(
                            "call"
                        )
                        == call
                    ):
                        self._active.pop(
                            tg,
                            None,
                        )

                self._last_event = {
                    key: value
                    for key, value
                    in normalized.items()
                    if key != "_seen"
                }

                self._updated_at = (
                    received_at
                )

            #
            # Auch ein STOP, das den
            # aktiven TG-State nicht
            # verändert, ist für
            # Last-Seen/Buddies relevant.
            #
            changed = True

        elif topic in {
            "/server/state/loginz",
            "/server/state/logins",
        }:
            try:
                count = int(
                    payload
                )
            except ValueError:
                return

            with self._lock:
                if (
                    self._client_count
                    != count
                ):
                    self._client_count = (
                        count
                    )

                    changed = True

                self._updated_at = (
                    datetime.now()
                    .astimezone()
                    .isoformat()
                )

        if changed:
            self._notify()

    def _purge_stale_locked(
        self,
    ) -> None:
        if (
            self.stale_after
            <= 0
        ):
            return

        cutoff = (
            time.time()
            - self.stale_after
        )

        stale = [
            tg
            for tg, entry
            in self._active.items()
            if float(
                entry.get(
                    "_seen",
                    0,
                )
            )
            < cutoff
        ]

        for tg in stale:
            self._active.pop(
                tg,
                None,
            )

    def snapshot(
        self,
    ) -> dict[str, Any]:
        with self._lock:
            self._purge_stale_locked()

            entries = sorted(
                self._active.values(),
                key=lambda item:
                    float(
                        item.get(
                            "_seen",
                            0,
                        )
                    ),
                reverse=True,
            )

            live = [
                {
                    key: value
                    for key, value
                    in entry.items()
                    if key != "_seen"
                }
                for entry in entries
            ]

            return {
                "available":
                    self._connected,

                "source":
                    "FM-Funknetz MQTT",

                "active":
                    (
                        live[0]
                        if live
                        else None
                    ),

                "live":
                    live,

                "last_heard":
                    [],

                "client_count":
                    self._client_count,

                "updated_at":
                    self._updated_at,

                "reason":
                    (
                        "Echtzeit-Talker aus FM-Funknetz MQTT."
                        if self._connected
                        else
                        "FM-Funknetz MQTT momentan nicht verbunden."
                    ),

                "mqtt": {
                    "configured":
                        True,

                    "adapter_active":
                        True,

                    "connected":
                        self._connected,

                    "host":
                        self.host,

                    "port":
                        self.port,

                    "topics":
                        list(
                            self.topics
                        ),

                    "last_event":
                        self._last_event,
                },
            }

    def _notify(
        self,
    ) -> None:
        callback = (
            self._on_update
        )

        if callback is None:
            return

        try:
            callback(
                self.snapshot()
            )
        except Exception:
            pass

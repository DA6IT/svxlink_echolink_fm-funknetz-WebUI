from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

from .secure_http import https_urlopen


class FMStatsDirectory:
    """
    Read-only client for the public FM-Funknetz statistics API.

    Used to discover callsign/device variants such as:

        DO1DX
        DO1DX-APP
        DO1DX-HS

    This is deliberately separate from the MQTT node directory:
    - Stats API: known/used callsign variants
    - Node MQTT: current online state
    - Talk MQTT: current speech activity
    """

    def __init__(
        self,
        url: str,
        cache_ttl: int = 300,
    ) -> None:
        self.url = url
        self.cache_ttl = max(
            30,
            int(cache_ttl),
        )

        self._lock = (
            threading.RLock()
        )

        self._cache: dict[
            str,
            tuple[
                float,
                dict[str, Any],
            ],
        ] = {}

    @staticmethod
    def _call(
        value: Any,
    ) -> str:
        return (
            str(value or "")
            .strip()
            .upper()
        )

    @staticmethod
    def _number(
        value: Any,
    ) -> float | int | None:
        if value is None:
            return None

        try:
            number = float(
                value
            )

            if number.is_integer():
                return int(
                    number
                )

            return number

        except (
            TypeError,
            ValueError,
        ):
            return None

    def call_detail(
        self,
        callsign: str,
    ) -> dict[str, Any]:
        call = self._call(
            callsign
        )

        if not call:
            return {
                "available": True,
                "call": "",
                "matched_by": None,
                "summary": {},
                "devices": [],
                "by_tg": [],
            }

        now = time.time()

        with self._lock:
            cached = (
                self._cache.get(
                    call
                )
            )

            if (
                cached
                and cached[0] > now
            ):
                return cached[1]

        params = urllib.parse.urlencode(
            {
                "mode":
                    "call_detail",

                "call":
                    call,
            }
        )

        request = (
            urllib.request.Request(
                f"{self.url}?{params}",
                headers={
                    "User-Agent":
                        "svxlink-webui/0.6",

                    "Accept":
                        "application/json",
                },
            )
        )

        try:
            with https_urlopen(
                request,
                timeout=8,
            ) as response:
                raw = (
                    response.read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )

            data = json.loads(
                raw
            )

        except Exception as exc:
            return {
                "available":
                    False,

                "call":
                    call,

                "matched_by":
                    None,

                "summary":
                    {},

                "devices":
                    [],

                "by_tg":
                    [],

                "reason":
                    str(exc),
            }

        if (
            not isinstance(
                data,
                dict,
            )
        ):
            return {
                "available": False,
                "call": call,
                "matched_by": None,
                "summary": {},
                "devices": [],
                "by_tg": [],
                "reason":
                    "Invalid response",
            }

        if data.get(
            "error"
        ):
            return {
                "available": False,
                "call": call,
                "matched_by":
                    data.get(
                        "matchedBy"
                    ),

                "summary":
                    data.get(
                        "summary"
                    )
                    or {},

                "devices":
                    [],

                "by_tg":
                    [],

                "reason":
                    str(
                        data.get(
                            "details"
                        )
                        or data.get(
                            "error"
                        )
                    ),
            }

        devices: list[
            dict[str, Any]
        ] = []

        for row in (
            data.get(
                "byDevice"
            )
            or []
        ):
            if not isinstance(
                row,
                dict,
            ):
                continue

            device_call = (
                self._call(
                    row.get(
                        "call"
                    )
                )
            )

            if not device_call:
                continue

            devices.append(
                {
                    "call":
                        device_call,

                    "sessions":
                        self._number(
                            row.get(
                                "cnt"
                            )
                        ),

                    "duration":
                        self._number(
                            row.get(
                                "dur"
                            )
                        ),

                    "average_duration":
                        self._number(
                            row.get(
                                "avgDur"
                            )
                        ),

                    "last_seen_epoch":
                        self._number(
                            row.get(
                                "lastTs"
                            )
                        ),

                    "share":
                        self._number(
                            row.get(
                                "share"
                            )
                        ),
                }
            )

        by_tg: list[
            dict[str, Any]
        ] = []

        for row in (
            data.get(
                "byTG"
            )
            or []
        ):
            if not isinstance(
                row,
                dict,
            ):
                continue

            tg = str(
                row.get(
                    "tg",
                    "",
                )
            ).strip()

            if not tg:
                continue

            by_tg.append(
                {
                    "tg":
                        tg,

                    "sessions":
                        self._number(
                            row.get(
                                "cnt"
                            )
                        ),

                    "duration":
                        self._number(
                            row.get(
                                "dur"
                            )
                        ),

                    "average_duration":
                        self._number(
                            row.get(
                                "avgDur"
                            )
                        ),

                    "share":
                        self._number(
                            row.get(
                                "share"
                            )
                        ),
                }
            )

        result = {
            "available":
                True,

            "call":
                self._call(
                    data.get(
                        "call"
                    )
                    or call
                ),

            "matched_by":
                data.get(
                    "matchedBy"
                ),

            "summary":
                data.get(
                    "summary"
                )
                or {},

            "devices":
                devices,

            "by_tg":
                by_tg,
        }

        with self._lock:
            self._cache[
                call
            ] = (
                now
                + self.cache_ttl,
                result,
            )

        return result

from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

from .secure_http import https_urlopen


API_URL = (
    "https://dashboard.fm-funknetz.de/"
    "stats_api.php"
)

VALID_RANGES = {
    "24h",
    "7d",
    "30d",
}

CACHE_TTL = 60.0

_cache_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _duration_label(
    seconds: int | float,
) -> str:
    sec = max(
        0,
        int(round(float(seconds or 0))),
    )

    hours, rest = divmod(
        sec,
        3600,
    )

    minutes, seconds = divmod(
        rest,
        60,
    )

    if hours:
        return (
            f"{hours}h "
            f"{minutes:02d}m"
        )

    if minutes:
        return (
            f"{minutes}m "
            f"{seconds:02d}s"
        )

    return f"{seconds}s"


def _number(
    value: Any,
    default: float = 0,
) -> float:
    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return default


def _normalize_row(
    row: Any,
) -> dict[str, Any] | None:
    if not isinstance(
        row,
        dict,
    ):
        return None

    tg = str(
        row.get("tg") or ""
    ).strip()

    if (
        not tg
        or not tg.isdigit()
    ):
        return None

    duration = int(
        _number(
            row.get("dur")
        )
    )

    sessions = int(
        _number(
            row.get("cnt")
        )
    )

    callers = int(
        _number(
            row.get("callers")
        )
    )

    average = _number(
        row.get("avgDur")
    )

    share = _number(
        row.get("share")
    )

    return {
        "tg": tg,
        "dur": duration,
        "duration_label":
            _duration_label(
                duration
            ),

        "cnt": sessions,

        "callers": callers,

        "avgDur": average,
        "avg_duration_label":
            _duration_label(
                average
            ),

        "share": round(
            share,
            1,
        ),
    }


def _download(
    period: str,
) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "mode": "overview",
        "range": period,
        "server": "all",
        "group": "base",
        "kind": "all",
    })

    request = (
        urllib.request.Request(
            f"{API_URL}?{params}",
            headers={
                "Accept":
                    "application/json",

                "User-Agent":
                    (
                        "DA6IT-SvxLink-WebUI/"
                        "1.0"
                    ),
            },
        )
    )

    with https_urlopen(
        request,
        timeout=8,
    ) as response:
        raw = response.read()

    payload = json.loads(
        raw.decode(
            "utf-8"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "Ungültige Antwort der "
            "FM-Funknetz Statistik."
        )

    rows: list[dict[str, Any]] = []

    for raw_row in (
        payload.get("tgs")
        or []
    ):
        row = _normalize_row(
            raw_row
        )

        if row:
            rows.append(
                row
            )

    #
    # Wir sortieren selbst noch einmal,
    # auch wenn die offizielle API dies
    # derzeit bereits macht.
    #
    rows.sort(
        key=lambda item:
            item["dur"],
        reverse=True,
    )

    return {
        "range": period,

        "source":
            "FM-Funknetz Statistik",

        "source_url":
            API_URL,

        "reliable_from":
            payload.get(
                "reliableFrom"
            ),

        "reaches_before":
            payload.get(
                "reachesBefore"
            ),

        "talkgroups":
            rows,

        "fetched_at":
            time.time(),

        "stale":
            False,
    }


def get_top_talkgroups(
    period: str = "24h",
    limit: int = 5,
) -> dict[str, Any]:
    period = str(
        period
    ).strip()

    if period not in VALID_RANGES:
        raise ValueError(
            "Ungültiger Zeitraum."
        )

    limit = max(
        1,
        min(
            int(limit),
            20,
        ),
    )

    now = time.monotonic()

    with _cache_lock:
        cached = _cache.get(
            period
        )

        if (
            cached
            and now
            - cached["cache_time"]
            < CACHE_TTL
        ):
            result = dict(
                cached["result"]
            )

            result["talkgroups"] = (
                result[
                    "talkgroups"
                ][:limit]
            )

            return result

    try:
        result = _download(
            period
        )

    except Exception as exc:
        #
        # Bei einem kurzen API-Ausfall
        # lieber die letzte bekannte
        # Statistik anzeigen.
        #
        with _cache_lock:
            cached = _cache.get(
                period
            )

            if cached:
                result = dict(
                    cached["result"]
                )

                result["stale"] = True
                result["reason"] = (
                    "Offizielle Statistik "
                    "aktuell nicht erreichbar; "
                    "letzten Cache verwendet."
                )

                result["talkgroups"] = (
                    result[
                        "talkgroups"
                    ][:limit]
                )

                return result

        raise RuntimeError(
            "FM-Funknetz Statistik "
            f"nicht abrufbar: {exc}"
        ) from exc

    with _cache_lock:
        _cache[period] = {
            "cache_time": now,
            "result": result,
        }

    output = dict(
        result
    )

    output["talkgroups"] = (
        output[
            "talkgroups"
        ][:limit]
    )

    return output

from __future__ import annotations

import html
import re
import threading
import time
import urllib.request
from typing import Any

from .secure_http import https_urlopen


class FMTalkgroupNames:
    """
    Read-only cache for the official FM-Funknetz TG database.
    """

    def __init__(
        self,
        url: str,
        cache_ttl: int = 3600,
    ) -> None:
        self.url = url
        self.cache_ttl = max(60, int(cache_ttl))

        self._lock = threading.RLock()
        self._expires = 0.0
        self._names: dict[str, str] = {}
        self._updated_at: float | None = None

    @staticmethod
    def _clean_name(value: str) -> str:
        value = re.sub(
            r"<[^>]+>",
            "",
            value,
        )

        value = html.unescape(value)

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    def _load(self) -> None:
        now = time.time()

        with self._lock:
            if self._names and self._expires > now:
                return

        request = urllib.request.Request(
            self.url,
            headers={
                "User-Agent":
                    "svxlink-webui/0.7",

                "Accept":
                    "text/plain,*/*",
            },
        )

        try:
            with https_urlopen(
                request,
                timeout=8,
            ) as response:
                text = (
                    response
                    .read()
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                )
        except Exception:
            #
            # Alten Cache behalten,
            # falls FM-Funknetz kurz nicht erreichbar ist.
            #
            with self._lock:
                self._expires = (
                    now + 300
                )

            return

        names: dict[str, str] = {}

        #
        # Beispiel:
        # '2624' => ' Nordrhein-Westfalen',
        #
        pattern = re.compile(
            r"""['"](\d+)['"]\s*=>\s*['"](.+?)['"]\s*,""",
            re.MULTILINE,
        )

        for tg, name in pattern.findall(text):
            clean = self._clean_name(
                name
            )

            if not clean:
                continue

            names[str(int(tg))] = clean

        with self._lock:
            self._names = names
            self._updated_at = now
            self._expires = (
                now + self.cache_ttl
            )

    def all(
        self,
    ) -> dict[str, str]:
        self._load()

        with self._lock:
            return dict(
                self._names
            )

    def name(
        self,
        tg: Any,
    ) -> str | None:
        key = str(
            tg or ""
        ).strip()

        if not key:
            return None

        try:
            key = str(
                int(key)
            )
        except ValueError:
            pass

        return self.all().get(
            key
        )

    def status(
        self,
    ) -> dict[str, Any]:
        names = self.all()

        return {
            "source": self.url,
            "count": len(names),
            "updated_at": self._updated_at,
            "names": names,
        }

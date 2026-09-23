from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import HTTPException, Request


CSRF_HEADER = "x-svxlink-csrf"
CSRF_VALUE = "1"


def require_same_origin_write(
    request: Request,
) -> None:
    """
    Protect browser-triggered state-changing actions.

    HTTP Basic Auth credentials may be sent automatically by
    a browser. Therefore authentication alone is not a CSRF
    defense.

    Requirements:
    - explicit non-simple request header;
    - Origin must be present;
    - Origin host must exactly match the HTTP Host header.
    """

    csrf = (
        request.headers
        .get(
            CSRF_HEADER,
            "",
        )
        .strip()
    )

    if csrf != CSRF_VALUE:
        raise HTTPException(
            status_code=403,
            detail=(
                "CSRF-Schutz: "
                "Request-Header fehlt."
            ),
        )

    host = (
        request.headers
        .get(
            "host",
            "",
        )
        .strip()
        .lower()
    )

    origin = (
        request.headers
        .get(
            "origin",
            "",
        )
        .strip()
    )

    if not host or not origin:
        raise HTTPException(
            status_code=403,
            detail=(
                "CSRF-Schutz: "
                "Origin fehlt."
            ),
        )

    try:
        parsed = urlsplit(
            origin
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail=(
                "CSRF-Schutz: "
                "Ungültiger Origin."
            ),
        ) from exc

    if (
        parsed.scheme not in {
            "http",
            "https",
        }
        or not parsed.netloc
        or parsed.netloc.lower()
        != host
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "CSRF-Schutz: "
                "Cross-Origin-Request "
                "nicht erlaubt."
            ),
        )

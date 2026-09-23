from __future__ import annotations

import pytest

from fastapi import HTTPException
from starlette.requests import Request

from app.request_security import (
    require_same_origin_write,
)


def request(
    *,
    host: str = "shari.example.test",
    origin: str | None = (
        "https://shari.example.test"
    ),
    csrf: str | None = "1",
) -> Request:
    headers: list[
        tuple[bytes, bytes]
    ] = [
        (
            b"host",
            host.encode(),
        ),
    ]

    if origin is not None:
        headers.append(
            (
                b"origin",
                origin.encode(),
            )
        )

    if csrf is not None:
        headers.append(
            (
                b"x-svxlink-csrf",
                csrf.encode(),
            )
        )

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": (
            "/api/system/"
            "update/install"
        ),
        "raw_path": (
            b"/api/system/"
            b"update/install"
        ),
        "query_string": b"",
        "headers": headers,
        "client": (
            "127.0.0.1",
            12345,
        ),
        "server": (
            "shari.example.test",
            443,
        ),
    }

    return Request(
        scope
    )


def test_same_origin_allowed():
    require_same_origin_write(
        request()
    )


def test_missing_csrf_header_denied():
    with pytest.raises(
        HTTPException
    ) as exc:
        require_same_origin_write(
            request(
                csrf=None,
            )
        )

    assert (
        exc.value.status_code
        == 403
    )


def test_missing_origin_denied():
    with pytest.raises(
        HTTPException
    ) as exc:
        require_same_origin_write(
            request(
                origin=None,
            )
        )

    assert (
        exc.value.status_code
        == 403
    )


def test_cross_origin_denied():
    with pytest.raises(
        HTTPException
    ) as exc:
        require_same_origin_write(
            request(
                origin=(
                    "https://evil."
                    "example.test"
                ),
            )
        )

    assert (
        exc.value.status_code
        == 403
    )


def test_wrong_port_denied():
    with pytest.raises(
        HTTPException
    ) as exc:
        require_same_origin_write(
            request(
                origin=(
                    "https://"
                    "shari.example.test:"
                    "8443"
                ),
            )
        )

    assert (
        exc.value.status_code
        == 403
    )

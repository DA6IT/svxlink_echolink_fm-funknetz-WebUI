from __future__ import annotations

from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)


def validate_https_url(
    url: str,
) -> str:
    value = str(
        url or ""
    ).strip()

    parsed = urlsplit(
        value
    )

    if (
        parsed.scheme.lower()
        != "https"
    ):
        raise ValueError(
            "Nur HTTPS-URLs sind erlaubt."
        )

    if not parsed.hostname:
        raise ValueError(
            "URL enthält keinen gültigen Host."
        )

    if (
        parsed.username
        or parsed.password
    ):
        raise ValueError(
            "Credentials in URLs sind nicht erlaubt."
        )

    return value


class HTTPSOnlyRedirectHandler(
    HTTPRedirectHandler
):
    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        validate_https_url(
            newurl
        )

        return super().redirect_request(
            req,
            fp,
            code,
            msg,
            headers,
            newurl,
        )


def https_urlopen(
    request: Request | str,
    *,
    timeout: float,
):
    if isinstance(
        request,
        Request,
    ):
        url = request.full_url
    else:
        url = str(
            request
        )

    validate_https_url(
        url
    )

    opener = build_opener(
        HTTPSOnlyRedirectHandler()
    )

    return opener.open(
        request,
        timeout=timeout,
    )

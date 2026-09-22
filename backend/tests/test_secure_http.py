import pytest

from app.secure_http import (
    validate_https_url,
)


def test_https_url_allowed():
    assert (
        validate_https_url(
            "https://example.org/test"
        )
        == "https://example.org/test"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/",
        "file:///etc/passwd",
        "ftp://example.org/file",
        "data:text/plain,test",
        "javascript:alert(1)",
        "",
    ],
)
def test_non_https_urls_rejected(
    url,
):
    with pytest.raises(
        ValueError
    ):
        validate_https_url(
            url
        )


def test_credentials_in_url_rejected():
    with pytest.raises(
        ValueError
    ):
        validate_https_url(
            "https://user:password@example.org/"
        )

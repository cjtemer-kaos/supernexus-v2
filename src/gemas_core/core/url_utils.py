"""URL helpers — stdlib-only.

Ported from RUFUS ``utils.py::is_valid_url``. RUFUS uses
``urlparse`` and accepts only ``http``/``https``; we generalize
the accepted schemes via a kwarg so unit tests can opt in to
``ftp`` etc. Default behaviour is identical to RUFUS.

Why a kwarg instead of just two helpers: callers in the wider
gemas_core ecosystem sometimes need to check non-HTTP URLs
(mailto, ftp in test fixtures), and the function is cheap
enough that one parameter beats three near-duplicate functions.
"""
from __future__ import annotations

from typing import NamedTuple, Optional
from urllib.parse import urljoin, urlparse

__all__ = [
    "is_valid_url",
    "is_http_url",
    "normalize_url",
    "parse_url",
]

_DEFAULT_SCHEMES: tuple[str, ...] = ("http", "https")


def is_valid_url(
    url,
    *,
    schemes: tuple[str, ...] = _DEFAULT_SCHEMES,
) -> bool:
    """Return True iff ``url`` parses with an allowed scheme and a netloc.

    Defensive against non-string inputs (returns False) and against
    empty / whitespace-only strings. The check is intentionally
    strict: a scheme-only URL like ``https://`` is rejected because
    it has no netloc.

    Parameters
    ----------
    url:
        The URL to validate. May be any type; non-strings return
        False rather than raising.
    schemes:
        Tuple of allowed schemes (lower-case, no trailing colon).
        Defaults to ``("http", "https")`` to match RUFUS.

    Examples
    --------
    >>> is_valid_url("https://example.com/x")
    True
    >>> is_valid_url("javascript:alert(1)")
    False
    """
    if not isinstance(url, str):
        return False
    if not url or not url.strip():
        return False
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        # urlparse is very permissive; in practice this rarely fires,
        # but a malformed IDN or a control character can still raise.
        return False
    # urlparse normalises scheme to lower-case, so we don't have to.
    if parsed.scheme not in schemes:
        return False
    if not parsed.netloc:
        return False
    return True


def is_http_url(url) -> bool:
    """Convenience alias: ``is_valid_url(url)`` with default schemes."""
    return is_valid_url(url)


class _UrlParts(NamedTuple):
    """Subset of ``urllib.parse.ParseResult`` that we expose.

    We don't reuse ``ParseResult`` directly because it has more
    fields (username, password, hostname, port) than most callers
    want, and we want to be type-friendly without forcing callers
    to import ``urllib.parse``.
    """

    scheme: str
    netloc: str
    path: str
    params: str
    query: str
    fragment: str


def parse_url(url) -> Optional[_UrlParts]:
    """Parse a URL into a namedtuple, or return None if it's not a full URL.

    Relative URLs (e.g. ``"about"``) return None — use
    :func:`normalize_url` if you have a base to resolve them
    against. URLs with a scheme but no netloc (e.g. ``"https://"``)
    also return None.
    """
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return None
    if not parsed.scheme or not parsed.netloc:
        return None
    return _UrlParts(
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        path=parsed.path,
        params=parsed.params,
        query=parsed.query,
        fragment=parsed.fragment,
    )


def normalize_url(url: str, base: str = "") -> Optional[str]:
    """Resolve a possibly-relative URL against ``base`` and validate it.

    Returns the absolute URL string if the result is a valid HTTP
    URL, or None if the result is empty, has an unsafe scheme,
    or the base is invalid.

    Examples
    --------
    >>> normalize_url("about", base="https://example.com/x/")
    'https://example.com/x/about'
    >>> normalize_url("javascript:alert(1)", base="https://example.com/")
    """
    if not isinstance(url, str) or not url.strip():
        return None
    if base:
        if not is_valid_url(base):
            return None
        try:
            joined = urljoin(base, url)
        except (ValueError, TypeError):
            return None
    else:
        joined = url
    if not is_valid_url(joined):
        return None
    return joined

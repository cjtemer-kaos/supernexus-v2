"""Tests for core/url_utils.py — stdlib-only URL helpers ported
from RUFUS ``utils.py::is_valid_url``.

The original RUFUS version does ``urlparse`` then checks
``scheme in ("http", "https") and netloc``. We generalize it
slightly so callers can pass other schemes (e.g. ``ftp``) for
unit tests, but the default behaviour matches RUFUS exactly.
"""
from __future__ import annotations


from gemas_core.core.url_utils import (
    is_valid_url,
    is_http_url,
    normalize_url,
    parse_url,
)


class TestIsValidUrl:
    def test_https_with_netloc(self):
        assert is_valid_url("https://example.com/path") is True

    def test_http_with_netloc(self):
        assert is_valid_url("http://example.com") is True

    def test_https_with_query_and_fragment(self):
        assert (
            is_valid_url("https://example.com/q?x=1&y=2#frag") is True
        )

    def test_https_with_port(self):
        assert is_valid_url("https://example.com:8080/x") is True

    def test_https_with_subdomain(self):
        assert is_valid_url("https://api.v2.example.co.uk/a") is True

    def test_no_scheme_rejected(self):
        assert is_valid_url("example.com/path") is False

    def test_ftp_scheme_rejected_by_default(self):
        # RUFUS only allows http/https
        assert is_valid_url("ftp://example.com/file") is False

    def test_empty_string_rejected(self):
        assert is_valid_url("") is False

    def test_none_rejected(self):
        # Some callers pass None through accidental string concat
        assert is_valid_url(None) is False  # type: ignore[arg-type]

    def test_garbage_rejected(self):
        assert is_valid_url("not a url at all !!!") is False

    def test_whitespace_only_rejected(self):
        assert is_valid_url("   ") is False

    def test_scheme_only_rejected(self):
        # "https://" alone has no netloc
        assert is_valid_url("https://") is False

    def test_custom_schemes_accepted(self):
        # Caller can opt in to other schemes
        assert (
            is_valid_url("ftp://example.com/file", schemes=("http", "https", "ftp"))
            is True
        )

    def test_javascript_scheme_rejected(self):
        # XSS attempt — should never pass
        assert is_valid_url("javascript:alert(1)") is False

    def test_data_scheme_rejected(self):
        assert is_valid_url("data:text/html,<script>") is False

    def test_non_string_types_rejected(self):
        # Defensive: never crash on weird inputs
        assert is_valid_url(123) is False  # type: ignore[arg-type]
        assert is_valid_url([]) is False  # type: ignore[arg-type]
        assert is_valid_url({}) is False  # type: ignore[arg-type]

    def test_unicode_netloc_accepted(self):
        # Internationalized domain names (IDN) are valid
        assert is_valid_url("https://例え.jp/path") is True

    def test_scheme_case_sensitive_match(self):
        # urllib normalizes scheme to lowercase; "HTTPS://" should still pass
        assert is_valid_url("HTTPS://example.com/x") is True


class TestIsHttpUrl:
    def test_alias_for_is_valid_url_with_default_schemes(self):
        # The convenience function is just a 1-arg wrapper
        assert is_http_url("https://example.com") is True
        assert is_http_url("http://example.com") is True
        assert is_http_url("ftp://example.com") is False


class TestNormalizeUrl:
    def test_relative_path_against_base(self):
        result = normalize_url("about", base="https://example.com/x/")
        assert result == "https://example.com/x/about"

    def test_absolute_url_passes_through(self):
        result = normalize_url(
            "https://other.com/x", base="https://example.com/"
        )
        assert result == "https://other.com/x"

    def test_protocol_relative(self):
        result = normalize_url("//cdn.example.com/x.js", base="https://example.com/page")
        # urljoin with a https base will produce https
        assert result == "https://cdn.example.com/x.js"

    def test_anchor_only(self):
        # urljoin treats #section as a fragment replacement
        # *appended* to the existing query (RFC 3986 reference
        # resolution — query + fragment is a single ref).
        result = normalize_url("#section", base="https://example.com/page?q=1")
        assert result == "https://example.com/page?q=1#section"

    def test_empty_url_returns_none(self):
        # An empty input is not a valid URL to consume
        assert normalize_url("") is None

    def test_empty_base_and_relative_returns_none(self):
        # Can't normalize a relative URL without a base
        assert normalize_url("about") is None

    def test_invalid_scheme_returns_none(self):
        # A scheme we don't accept (javascript:) should be rejected
        assert normalize_url("javascript:alert(1)", base="https://example.com/") is None

    def test_invalid_base_returns_none(self):
        assert normalize_url("about", base="not a base") is None

    def test_query_preserved(self):
        result = normalize_url(
            "x?a=1&b=2", base="https://example.com/dir/"
        )
        assert result == "https://example.com/dir/x?a=1&b=2"

    def test_returns_string_for_valid(self):
        # Type check: returns str, not None
        result = normalize_url("https://example.com/")
        assert isinstance(result, str)


class TestParseUrl:
    def test_returns_namedtuple(self):
        result = parse_url("https://user:pass@example.com:8080/x?y=1#z")
        # Should have at least these 6 fields
        assert result.scheme == "https"
        assert result.netloc == "user:pass@example.com:8080"
        assert result.path == "/x"
        assert result.params == ""
        assert result.query == "y=1"
        assert result.fragment == "z"

    def test_invalid_url_returns_none(self):
        # Garbage input — urlparse will succeed but with empty netloc
        # We treat that as invalid by checking netloc presence
        assert parse_url("not a url") is None

    def test_relative_path_returns_none(self):
        # parse_url expects a full URL, not a relative one
        assert parse_url("about") is None

    def test_scheme_only_returns_none(self):
        assert parse_url("https://") is None

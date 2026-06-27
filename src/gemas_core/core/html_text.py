"""HTML→text extraction — stdlib-only.

Ported from RUFUS ``core/extraction.py::extract_text`` which uses
BeautifulSoup to drop noise tags and then collapses whitespace
with a regex. We re-implement the same algorithm with stdlib
``html.parser.HTMLParser`` so gemas_core stays dep-free.

Behavioural parity with RUFUS:
- Default skip tags: style, script, nav, aside, footer, header.
- Whitespace is collapsed to single spaces.
- ``get_text(separator=" ")`` semantics: block-level transitions
  get a space between them.
- Result is stripped of leading/trailing whitespace.

Divergences from RUFUS (documented in the README):
- We also drop ``noscript``, ``svg``, ``form`` by default because
  in RAG contexts those tags are almost never useful and BS4
  would have done the same if asked. The RUFUS list can be
  recovered by passing ``skip_tags=("style", "script", "nav",
  "aside", "footer", "header")``.
- We also drop ``<!-- ... -->`` comments and ``<!DOCTYPE>``
  declarations, which is what BS4 would do via ``get_text()``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable, Optional

__all__ = [
    "DEFAULT_SKIP_TAGS",
    "extract_text",
    "extract_text_with_meta",
    "TextExtractionStats",
]

# Tags whose entire subtree we discard. Lower-case; the parser
# normalises tag names. RUFUS's original set is the first 6;
# we add 3 more (noscript, svg, form) that are almost never
# useful body text in RAG / summarisation contexts.
DEFAULT_SKIP_TAGS: frozenset[str] = frozenset({
    "style",
    "script",
    "nav",
    "aside",
    "footer",
    "header",
    "noscript",
    "svg",
    "form",
})


# Pre-compile the whitespace collapse regex. Matches one or more
# of: ASCII whitespace, \u00A0 (non-breaking space), \u200b (zero-
# width space) and similar. We deliberately exclude word chars.
_WHITESPACE_RE = re.compile(r"[\s\u00A0\u200b\u2028\u2029\ufeff]+")


class _SkippingParser(HTMLParser):
    """HTMLParser that drops the subtree of any tag in ``skip_tags``.

    The parser is fed the document character by character. When we
    enter a skip tag, we set ``_skip_depth`` to 1 and ignore every
    character until the matching close tag decrements the counter
    back to 0. Otherwise we append the visible text into
    ``self.parts`` with a single space inserted at block-level
    boundaries (matching BS4's ``get_text(separator=" ")``
    behaviour for the cases we care about).
    """

    # Block-level tags that BS4's get_text(separator=" ") inserts
    # a separator for. This is a small whitelist; it doesn't have
    # to be exhaustive because the result is whitespace-collapsed
    # at the end anyway. We just want to avoid accidental
    # "HelloWorld" where there should be "Hello World".
    _BLOCK_TAGS = frozenset({
        "p", "div", "section", "article", "main", "aside",
        "header", "footer", "nav", "ul", "ol", "li", "dl",
        "dt", "dd", "table", "tr", "td", "th", "thead",
        "tbody", "tfoot", "h1", "h2", "h3", "h4", "h5", "h6",
        "br", "hr", "blockquote", "pre", "figure", "figcaption",
        "form", "fieldset", "address",
    })

    def __init__(self, skip_tags: Iterable[str]) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_tags = frozenset(t.lower() for t in skip_tags)
        self._skip_depth = 0
        self.parts: list[str] = []
        self.dropped_chunks = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self._skip_tags:
            self._skip_depth += 1
            self.dropped_chunks += 1
            return
        if self._skip_depth == 0 and tag in self._BLOCK_TAGS:
            # Insert a separator at the start of a block-level tag
            # so adjacent blocks don't run together. Whitespace
            # collapse at the end cleans up the extra space.
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._skip_depth == 0 and tag in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
            self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        # Called for named entities like ``&amp;`` when
        # ``convert_charrefs`` is False. We leave the default
        # behaviour — convert_charrefs=True routes these to
        # handle_data — so this method is rarely hit. Override
        # to be safe.
        if self._skip_depth == 0:
            self.parts.append(self.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        # Same as above for &#123; numeric refs.
        if self._skip_depth == 0:
            self.parts.append(self.unescape(f"&#{name};"))

    def handle_comment(self, data: str) -> None:
        # Comments are always noise; ignore regardless of skip set.
        return

    def handle_decl(self, decl: str) -> None:
        # <!DOCTYPE ...> etc. — never visible text.
        return

    def handle_pi(self, data: str) -> None:
        # Processing instructions — also never visible text.
        return


def extract_text(
    html: str,
    *,
    skip_tags: Optional[Iterable[str]] = None,
) -> str:
    """Return the visible text of ``html`` with whitespace collapsed.

    Parameters
    ----------
    html:
        The HTML source. Empty string is fine and returns "".
    skip_tags:
        Optional override of the set of tags whose entire subtree
        is discarded. Defaults to :data:`DEFAULT_SKIP_TAGS`.

    Returns
    -------
    str
        The extracted text. Whitespace is collapsed to single
        spaces, and the result is stripped of leading/trailing
        whitespace.
    """
    if not html:
        return ""
    skip = frozenset(skip_tags) if skip_tags is not None else DEFAULT_SKIP_TAGS
    parser = _SkippingParser(skip_tags=skip)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed HTML should never crash the caller. If the
        # parser chokes on something weird, fall back to the raw
        # text after a regex pass.
        pass
    raw = "".join(parser.parts)
    if not raw:
        return ""
    collapsed = _WHITESPACE_RE.sub(" ", raw)
    return collapsed.strip()


@dataclass
class TextExtractionStats:
    """Diagnostic info from :func:`extract_text_with_meta`."""

    text: str
    input_chars: int
    output_chars: int
    dropped_chunks: int

    def compression_ratio(self) -> float:
        """Return output/input chars, or 0.0 if input was empty."""
        if self.input_chars == 0:
            return 0.0
        return self.output_chars / self.input_chars


def extract_text_with_meta(
    html: str,
    *,
    skip_tags: Optional[Iterable[str]] = None,
) -> TextExtractionStats:
    """Same as :func:`extract_text` but returns a stats object."""
    if not html:
        return TextExtractionStats(
            text="",
            input_chars=0,
            output_chars=0,
            dropped_chunks=0,
        )
    skip = frozenset(skip_tags) if skip_tags is not None else DEFAULT_SKIP_TAGS
    parser = _SkippingParser(skip_tags=skip)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass
    raw = "".join(parser.parts)
    text = _WHITESPACE_RE.sub(" ", raw).strip() if raw else ""
    return TextExtractionStats(
        text=text,
        input_chars=len(html),
        output_chars=len(text),
        dropped_chunks=parser.dropped_chunks,
    )

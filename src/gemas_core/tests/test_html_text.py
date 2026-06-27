"""Tests for core/html_text.py — stdlib-only HTML→text extractor.

Ported from RUFUS ``core/extraction.py::extract_text`` which uses
BeautifulSoup to drop noise tags (``style``, ``script``, ``nav``,
``aside``, ``footer``, ``header``) and then collapses whitespace
with a regex.

We re-implement the same algorithm with stdlib ``html.parser`` so
gemas_core stays dep-free. Output should match the RUFUS behaviour
for the canonical cases we test against.
"""
from __future__ import annotations


from gemas_core.core.html_text import (
    DEFAULT_SKIP_TAGS,
    extract_text,
    extract_text_with_meta,
    TextExtractionStats,
)


class TestExtractText:
    def test_empty_string(self):
        assert extract_text("") == ""

    def test_plain_text_passthrough(self):
        assert extract_text("Hello world") == "Hello world"

    def test_simple_paragraph(self):
        html = "<p>Hello world</p>"
        assert extract_text(html) == "Hello world"

    def test_multiple_paragraphs_separated_by_space(self):
        # The RUFUS implementation uses " " as the separator; we do too.
        html = "<p>First.</p><p>Second.</p>"
        assert extract_text(html) == "First. Second."

    def test_nested_tags(self):
        html = "<div><p>Outer <b>inner</b> end</p></div>"
        assert extract_text(html) == "Outer inner end"

    def test_script_tag_content_dropped(self):
        html = "<p>Before</p><script>alert('xss');</script><p>After</p>"
        assert extract_text(html) == "Before After"
        # Critically, the JS body is gone
        assert "alert" not in extract_text(html)

    def test_style_tag_content_dropped(self):
        html = "<p>Before</p><style>body { color: red; }</style><p>After</p>"
        out = extract_text(html)
        assert out == "Before After"
        assert "color" not in out
        assert "{" not in out

    def test_nav_tag_dropped(self):
        html = "<nav><a href='/x'>link</a></nav><main>content</main>"
        out = extract_text(html)
        assert "link" not in out
        assert "content" in out

    def test_aside_tag_dropped(self):
        html = "<aside>sidebar text</aside><p>main</p>"
        out = extract_text(html)
        assert "sidebar" not in out
        assert "main" in out

    def test_footer_tag_dropped(self):
        html = "<p>content</p><footer>© 2026</footer>"
        out = extract_text(html)
        assert "content" in out
        assert "©" not in out

    def test_header_tag_dropped(self):
        html = "<header>site title</header><p>body</p>"
        out = extract_text(html)
        assert "site title" not in out
        assert "body" in out

    def test_noscript_tag_dropped(self):
        html = "<p>main</p><noscript>enable JS</noscript>"
        out = extract_text(html)
        assert "main" in out
        assert "enable JS" not in out

    def test_svg_content_dropped(self):
        # svg is a noise tag in extraction contexts
        html = "<p>main</p><svg><text>vector</text></svg>"
        out = extract_text(html)
        assert "main" in out
        assert "vector" not in out

    def test_form_tag_dropped(self):
        # forms are noise in extracted body text
        html = "<form><input name='q'/><button>search</button></form><p>body</p>"
        out = extract_text(html)
        assert "body" in out
        # The button text is also dropped because we drop the whole form subtree
        assert "search" not in out

    def test_whitespace_collapsed(self):
        # Tabs, newlines, multiple spaces → single space
        html = "<p>hello\n\n   world\t\t!</p>"
        assert extract_text(html) == "hello world !"

    def test_leading_trailing_whitespace_stripped(self):
        html = "<p>   hello   </p>"
        assert extract_text(html) == "hello"

    def test_html_entities_decoded(self):
        # &amp; → & etc. (html.parser handles this)
        html = "<p>Tom &amp; Jerry</p>"
        assert extract_text(html) == "Tom & Jerry"

    def test_named_entities_decoded(self):
        html = "<p>3 &lt; 5 &amp;&amp; 5 &gt; 3</p>"
        assert extract_text(html) == "3 < 5 && 5 > 3"

    def test_numeric_entities_decoded(self):
        html = "<p>&#x00A9; 2026</p>"  # ©
        assert extract_text(html) == "© 2026"

    def test_attributes_dropped(self):
        # href, class, id, etc. are never text
        html = '<a href="/x" class="big" id="y">link text</a>'
        assert extract_text(html) == "link text"

    def test_script_inside_attribute_still_dropped(self):
        # Tricky edge: <p onclick="bad()">safe</p> — the JS is in
        # an attribute, not a tag body. extract_text doesn't see it
        # as text at all. We just want the visible text.
        html = '<p onclick="bad()">safe</p>'
        assert extract_text(html) == "safe"

    def test_comments_dropped(self):
        html = "<p>before</p><!-- secret --><p>after</p>"
        assert extract_text(html) == "before after"

    def test_doctype_dropped(self):
        html = "<!DOCTYPE html><p>body</p>"
        assert extract_text(html) == "body"

    def test_cdata_dropped_as_text(self):
        # html.parser renders CDATA content but we want script-style noise gone
        html = "<script>/* <![CDATA[ */ var x = 1; /* ]]> */</script><p>visible</p>"
        out = extract_text(html)
        assert "visible" in out
        assert "var x" not in out

    def test_case_insensitive_tag_matching(self):
        # Browsers / BeautifulSoup treat tags case-insensitively
        html = "<P>uppercase</P>"
        assert extract_text(html) == "uppercase"

    def test_self_closing_void_elements(self):
        html = "<p>line1<br/>line2</p>"
        # br is a void element; the parser handles it; we just verify
        # the visible text is concatenated
        out = extract_text(html)
        assert "line1" in out
        assert "line2" in out

    def test_malformed_html_does_not_crash(self):
        # Unclosed tags, mismatched tags, etc.
        html = "<p>unclosed<b>bold"
        # Should not raise; output contains the text we have
        out = extract_text(html)
        assert "unclosed" in out
        assert "bold" in out

    def test_html_with_only_noise_returns_empty(self):
        html = "<script>x</script><style>y</style>"
        assert extract_text(html) == ""

    def test_default_skip_tags_includes_canonical_set(self):
        # Lock down the set so future changes are intentional
        expected = {
            "style", "script", "nav", "aside", "footer",
            "header", "noscript", "svg", "form",
        }
        assert set(DEFAULT_SKIP_TAGS) == expected


class TestExtractTextWithMeta:
    def test_returns_stats(self):
        html = "<p>hello</p><script>drop</script>"
        result = extract_text_with_meta(html)
        assert isinstance(result, TextExtractionStats)
        assert result.text == "hello"

    def test_stats_track_dropped_chunks(self):
        html = "<p>keep</p><script>drop1</script><style>drop2</style>"
        result = extract_text_with_meta(html)
        assert result.dropped_chunks == 2
        assert result.text == "keep"

    def test_stats_track_input_chars(self):
        html = "<p>hello</p>"
        result = extract_text_with_meta(html)
        assert result.input_chars == len(html)
        assert result.output_chars == len(result.text)

    def test_empty_input(self):
        result = extract_text_with_meta("")
        assert result.text == ""
        assert result.input_chars == 0
        assert result.output_chars == 0
        assert result.dropped_chunks == 0

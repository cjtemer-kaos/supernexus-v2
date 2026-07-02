#!/usr/bin/env python3
"""
book-to-skill: Document text extraction engine.
Extracts text from PDF, EPUB, DOCX, RTF, HTML, MOBI formats.
Graceful fallbacks from best library → stdlib → error.
"""

import json
import os
import re
import sys
from pathlib import Path


def extract_text(filepath: str, mode: str = "text") -> dict:
    filepath = str(filepath)
    ext = os.path.splitext(filepath)[1].lower()
    result = {"source": filepath, "format": ext, "mode": mode, "text": "", "pages": 0, "chapters": []}

    if not os.path.exists(filepath):
        result["error"] = "File not found"
        return result

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    result["file_size_mb"] = round(size_mb, 2)

    if ext == ".pdf":
        result["text"] = _extract_pdf(filepath, mode)
    elif ext in (".epub",):
        result["text"] = _extract_epub(filepath)
    elif ext in (".docx", ".doc"):
        result["text"] = _extract_docx(filepath)
    elif ext in (".rtf",):
        result["text"] = _extract_rtf(filepath)
    elif ext in (".html", ".htm", ".xhtml"):
        result["text"] = _extract_html(filepath)
    elif ext in (".mobi", ".azw", ".azw3"):
        result["text"] = _extract_mobi(filepath)
    elif ext in (".txt", ".md", ".markdown"):
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            result["text"] = f.read()
    else:
        result["error"] = f"Unsupported format: {ext}"

    if result["text"]:
        result["chars"] = len(result["text"])
        result["words"] = len(result["text"].split())
        result["estimated_tokens"] = result["chars"] // 4
        result["chapters"] = _detect_chapters(result["text"])

    return result


def _extract_pdf(filepath: str, mode: str) -> str:
    for method_key, method_fn in [
        ("docling", _try_docling),
        ("pdftotext", _try_pdftotext),
        ("pypdf2", _try_pypdf2),
        ("pdfminer", _try_pdfminer),
    ]:
        try:
            text = method_fn(filepath)
            if text and len(text.strip()) > 100:
                return text
        except Exception:
            continue
    return ""


def _try_docling(filepath: str) -> str:
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        doc = converter.convert(filepath)
        return doc.text or ""
    except ImportError:
        raise


def _try_pdftotext(filepath: str) -> str:
    import subprocess
    result = subprocess.run(["pdftotext", filepath, "-"], capture_output=True, text=True, timeout=30)
    return result.stdout if result.returncode == 0 else ""


def _try_pypdf2(filepath: str) -> str:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        raise


def _try_pdfminer(filepath: str) -> str:
    try:
        from pdfminer.high_level import extract_text as pm_extract
        return pm_extract(filepath)
    except ImportError:
        raise


def _extract_epub(filepath: str) -> str:
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(filepath)
        texts = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                texts.append(soup.get_text(separator="\n"))
        return "\n".join(texts)
    except ImportError:
        return _epub_stdlib(filepath)


def _epub_stdlib(filepath: str) -> str:
    import zipfile
    from html.parser import HTMLParser

    class TextCollector(HTMLParser):
        def __init__(self):
            super().__init__()
            self.texts = []
            self._capture = False
        def handle_starttag(self, tag, attrs):
            if tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th"):
                self._capture = True
        def handle_data(self, data):
            if self._capture:
                self.texts.append(data.strip())
            self._capture = False
        def handle_endtag(self, tag):
            if tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "br"):
                self.texts.append("\n")

    texts = []
    with zipfile.ZipFile(filepath) as z:
        for name in z.namelist():
            if name.endswith((".xhtml", ".html", ".htm")):
                content = z.read(name).decode("utf-8", errors="replace")
                parser = TextCollector()
                parser.feed(content)
                texts.extend(parser.texts)
    return "\n".join(texts)


def _extract_docx(filepath: str) -> str:
    try:
        from docx import Document
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        return _docx_stdlib(filepath)


def _docx_stdlib(filepath: str) -> str:
    import zipfile
    from xml.etree import ElementTree
    texts = []
    with zipfile.ZipFile(filepath) as z:
        if "word/document.xml" in z.namelist():
            tree = ElementTree.parse(z.open("word/document.xml"))
            root = tree.getroot()
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
                if t.text:
                    texts.append(t.text)
    return "\n".join(texts)


def _extract_rtf(filepath: str) -> str:
    try:
        from striprtf.striprtf import rtf_to_text
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return rtf_to_text(f.read())
    except ImportError:
        return _rtf_strip_fallback(filepath)


def _rtf_strip_fallback(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    text = re.sub(r"\\[a-z]+(?:[-']?\d+)?", " ", text)
    text = re.sub(r"\{|\}", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_html(filepath: str) -> str:
    try:
        from bs4 import BeautifulSoup
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n")
    except ImportError:
        from html.parser import HTMLParser

        class HtmlText(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
            def handle_data(self, data):
                if data.strip():
                    self.text.append(data.strip())
            def handle_endtag(self, tag):
                if tag in ("p", "br", "h1", "h2", "h3", "h4", "li"):
                    self.text.append("\n")

        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            parser = HtmlText()
            parser.feed(f.read())
            return "\n".join(parser.text)


def _extract_mobi(filepath: str) -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["ebook-convert", filepath, "/dev/stdout", "--output-profile=default"],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout[:100000] if result.returncode == 0 else ""
    except Exception:
        return ""


def _detect_chapters(text: str) -> list:
    chapters = []
    patterns = [
        r"^\s*(?:Chapter|CHAPTER|Ch\.|Capítulo|Sección|Section|Part|Parte)\s+[0-9IVXLCDM]+",
        r"^\s*(?:#+)\s+[A-Z]",
        r"^\s*\d+\.\s+[A-Z]",
    ]
    for i, line in enumerate(text.split("\n")[:500]):
        for p in patterns:
            if re.match(p, line):
                chapters.append({"line": i + 1, "heading": line.strip()[:80]})
                break
    return chapters


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract text from documents")
    parser.add_argument("path", help="Path to document")
    parser.add_argument("--mode", choices=["technical", "text"], default="text")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--install-missing", choices=["yes", "no", "ask"], default="ask")
    args = parser.parse_args()

    result = extract_text(args.path, args.mode)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Format: {result['format']}")
        print(f"Chars: {result.get('chars', 0):,}")
        print(f"Words: {result.get('words', 0):,}")
        print(f"Tokens: {result.get('estimated_tokens', 0):,}")
        print(f"Chapters: {len(result.get('chapters', []))}")
        if result.get("text"):
            print(f"\n--- Preview (first 2000 chars) ---\n{result['text'][:2000]}")
        if result.get("error"):
            print(f"\nERROR: {result['error']}")


if __name__ == "__main__":
    main()

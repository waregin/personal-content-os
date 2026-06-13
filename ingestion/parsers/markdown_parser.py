"""Parse a Markdown file into chunk dicts ready for embedding and DB insertion.

Public API:
    metadata, chunks = parse(filepath)
"""

import re
from datetime import date
from pathlib import Path

from .utils import make_chunks, merge_short, split_paragraphs

# Markdown syntax to strip from stored text
_STRIP_PATTERNS = [
    (re.compile(r"^#{1,6}\s+", re.MULTILINE), ""),        # headings
    (re.compile(r"\*\*(.+?)\*\*"), r"\1"),                 # bold
    (re.compile(r"\*(.+?)\*"), r"\1"),                     # italic
    (re.compile(r"__(.+?)__"), r"\1"),                     # bold alt
    (re.compile(r"_(.+?)_"), r"\1"),                       # italic alt
    (re.compile(r"`{1,3}(.+?)`{1,3}", re.DOTALL), r"\1"), # inline/fenced code
    (re.compile(r"!\[.*?\]\(.*?\)"), ""),                  # images
    (re.compile(r"\[(.+?)\]\(.*?\)"), r"\1"),              # links → keep label
    (re.compile(r"^[-*+]\s+", re.MULTILINE), ""),          # unordered list markers
    (re.compile(r"^\d+\.\s+", re.MULTILINE), ""),          # ordered list markers
    (re.compile(r"^>\s*", re.MULTILINE), ""),              # blockquotes
    (re.compile(r"^---+$", re.MULTILINE), ""),             # horizontal rules
    (re.compile(r"\s+"), " "),                             # collapse whitespace
]


def _strip_markdown(text: str) -> str:
    for pattern, replacement in _STRIP_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body) if YAML frontmatter is present."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}, text
    fm_block = match.group(1)
    body = text[match.end():]
    fm: dict = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm, body


def _extract_title(body: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    return match.group(1).strip() if match else None


def parse(filepath: str | Path) -> tuple[dict, list[dict]]:
    """Parse a Markdown file.

    Returns:
        metadata: dict with 'title' (str|None) and 'doc_date' (date|None)
        chunks:   list of chunk dicts ready for embedding and DB insertion
    """
    text = Path(filepath).read_text(encoding="utf-8")

    fm, body = _parse_frontmatter(text)

    title = _extract_title(body)

    doc_date: date | None = None
    if "date" in fm:
        try:
            doc_date = date.fromisoformat(fm["date"])
        except ValueError:
            pass

    metadata = {"title": title, "doc_date": doc_date}

    paragraphs = merge_short(split_paragraphs(body))
    chunks = make_chunks([_strip_markdown(p) for p in paragraphs], source_type="published-article")

    return metadata, chunks

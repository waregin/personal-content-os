"""Parse a plain-text file into chunk dicts ready for embedding and DB insertion.

Public API:
    metadata, chunks = parse(filepath)
"""

from pathlib import Path

from .utils import make_chunks, merge_short, split_paragraphs


def parse(filepath: str | Path) -> tuple[dict, list[dict]]:
    """Parse a plain-text file.

    Returns:
        metadata: dict with 'title' (None) and 'doc_date' (None)
        chunks:   list of chunk dicts ready for embedding and DB insertion
    """
    text = Path(filepath).read_text(encoding="utf-8")
    metadata = {"title": None, "doc_date": None}
    paragraphs = merge_short(split_paragraphs(text))
    chunks = make_chunks(paragraphs, source_type="unpublished-draft")
    return metadata, chunks

"""Shared utilities for all parsers in this package."""

import re

MIN_CHUNK_CHARS = 100


def split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


def merge_short(paragraphs: list[str]) -> list[str]:
    """Merge paragraphs shorter than MIN_CHUNK_CHARS into the next paragraph."""
    result: list[str] = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        # If this paragraph is short, merge forward into the next one
        while len(para) < MIN_CHUNK_CHARS and i + 1 < len(paragraphs):
            i += 1
            para = para + " " + paragraphs[i]
        result.append(para)
        i += 1
    return result

def make_chunks(paragraphs: list[str], source_type: str) -> list[dict]:
    return [
        {
            "chunk_text": para,
            "chunk_index": idx,
            "source_type": source_type,
            "corpus_type": "personal",
            "origin": "human-written",
            "send_to_api": "ask",
            "voice_eligible": True,
            "position_eligible": True,
            "topic_tags": [],
        }
        for idx, para in enumerate(paragraphs)
        if para
    ]

"""Shared data models for the autocomplete project."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class SentenceRecord:
    """Internal representation of a sentence loaded from a file.

    `line_number` is one-based: the first physical line in each source file is
    line 1. Blank lines still count toward this number even when skipped by the
    loader.
    """

    original_text: str
    normalized_text: str
    source_path: str
    line_number: int


@dataclass
class AutoCompleteData:
    """Autocomplete result required by the assignment."""

    completed_sentence: str
    source_text: str
    offset: int
    score: int


@dataclass(frozen=True)
class PreparedSentenceIndex:
    """Prepared records persisted by the Phase A data pipeline."""

    records: Tuple[SentenceRecord, ...]

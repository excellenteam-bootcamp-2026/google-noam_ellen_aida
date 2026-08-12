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


@dataclass
class Match:
    """Represents a successful match between query and sentence window.
    
    Used internally by matcher and scoring modules to communicate match details.
    """
    
    edit_type: str  # "exact", "substitution", "insertion", "deletion"
    edit_position: int | None  # 0-based index in query where edit occurred; None for exact
    matching_letters: int  # Length of the matching substring

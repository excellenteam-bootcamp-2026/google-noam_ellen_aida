"""Shared data models for the autocomplete project."""

from dataclasses import dataclass
from array import array
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
class NGramInvertedIndex:
    """Record-id postings for character n-gram candidate generation."""

    ngram_sizes: Tuple[int, ...]
    min_query_length: int
    postings: dict[int, dict[str, array]]


@dataclass(frozen=True)
class PreparedSentenceIndex:
    """Prepared records persisted by the Phase A data pipeline."""

    records: Tuple[SentenceRecord, ...]
    ngram_index: NGramInvertedIndex | None = None


@dataclass
class Match:
    """Represents a successful match between query and sentence window.
    
    Used internally by matcher and scoring modules to communicate match details.
    """
    
    edit_type: str  # "exact", "substitution", "insertion", "deletion"
    # 0-based index in query where edit occurred; None for exact.
    edit_position: int | None
    matching_letters: int  # Length of the matching substring

from dataclasses import dataclass


@dataclass
class SentenceRecord:
    """Internal representation of a sentence loaded from a file."""

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
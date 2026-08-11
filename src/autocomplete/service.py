"""Integration layer for autocomplete initialization and querying."""

from collections.abc import Iterable
from pathlib import Path

from .models import AutoCompleteData, SentenceRecord

_records: list[SentenceRecord] | None = None


def _load_index(index_path: Path) -> Iterable[SentenceRecord]:
    """Load the index through the data/index component."""

    from .index import load_index

    return load_index(index_path)


def _normalize(text: str) -> str:
    """Normalize text through the shared normalization component."""

    from .normalization import normalize

    return normalize(text)


def _find_best_match_score(prefix: str, sentence: str) -> int | None:
    """Score a sentence through the matching component."""

    from .matcher import find_best_match_score

    return find_best_match_score(prefix, sentence)


def initialize(index_path: Path) -> None:
    """Load the prepared sentence index used by subsequent queries."""

    if not index_path.is_file():
        raise FileNotFoundError(f"Prepared index not found: {index_path}")

    loaded_records = list(_load_index(index_path))
    if not all(isinstance(record, SentenceRecord) for record in loaded_records):
        raise TypeError("The prepared index must contain SentenceRecord objects")

    global _records
    _records = loaded_records


def get_best_k_completions(prefix: str) -> list[AutoCompleteData]:
    """Return the five highest-ranked completions for ``prefix``."""

    if _records is None:
        raise RuntimeError("Autocomplete service has not been initialized")

    normalized_prefix = _normalize(prefix)
    if not normalized_prefix:
        return []

    results: list[AutoCompleteData] = []
    for record in _records:
        score = _find_best_match_score(
            normalized_prefix,
            record.normalized_text,
        )
        if score is None:
            continue

        results.append(
            AutoCompleteData(
                completed_sentence=record.original_text,
                source_text=record.source_path,
                offset=record.line_number,
                score=score,
            )
        )

    results.sort(
        key=lambda result: (
            -result.score,
            result.completed_sentence.casefold(),
            result.source_text.casefold(),
            result.offset,
        )
    )
    return results[:5]

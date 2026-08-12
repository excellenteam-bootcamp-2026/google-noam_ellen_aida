"""Integration layer for autocomplete initialization and querying."""

from collections.abc import Iterable, Sequence
from pathlib import Path

from .models import AutoCompleteData, PreparedSentenceIndex, SentenceRecord
from .ngram import candidate_record_ids

_records: Sequence[SentenceRecord] | None = None
_index: PreparedSentenceIndex | None = None


def _load_index(index_path: Path) -> PreparedSentenceIndex:
    """Load the index through the data/index component."""

    from .index import load_index

    return load_index(index_path)


def _normalize(text: str) -> str:
    """Normalize text through the shared normalization component."""

    from .normalization import normalize_text

    return normalize_text(text)


def _find_best_match_score(prefix: str, sentence: str) -> int | None:
    """Score a sentence through the matching component."""

    from .matcher import find_best_match_score

    return find_best_match_score(prefix, sentence)


def initialize(index_path: Path) -> None:
    """Load the prepared sentence index used by subsequent queries."""

    if not index_path.is_file():
        raise FileNotFoundError(f"Prepared index not found: {index_path}")

    loaded_index = _load_index(index_path)
    if isinstance(loaded_index, PreparedSentenceIndex):
        loaded_records = loaded_index.records
    else:
        # Kept for tests or callers that monkeypatch the loader with records.
        loaded_records = list(loaded_index)
        loaded_index = None

    if not all(isinstance(record, SentenceRecord) for record in loaded_records):
        raise TypeError("The prepared index must contain SentenceRecord objects")

    global _records, _index
    _records = loaded_records
    _index = loaded_index


def get_best_k_completions(prefix: str) -> list[AutoCompleteData]:
    """Return the five highest-ranked completions for ``prefix``."""

    if _records is None:
        raise RuntimeError("Autocomplete service has not been initialized")

    if _index is not None and _records is _index.records:
        return search_index(prefix, _index)
    return search_records(prefix, _records)


def search_index(
    prefix: str,
    prepared_index: PreparedSentenceIndex,
) -> list[AutoCompleteData]:
    """Return completions using n-gram candidates and canonical verification."""

    normalized_prefix = _normalize(prefix)

    if not normalized_prefix:
        return []

    candidates = candidate_record_ids(
        normalized_prefix,
        prepared_index.records,
        prepared_index.ngram_index,
    )
    return _search_candidate_ids(normalized_prefix, prepared_index.records, candidates)


def search_records(
    prefix: str,
    records: Iterable[SentenceRecord],
) -> list[AutoCompleteData]:
    """Return the five highest-ranked completions from loaded records.

    This is the canonical linear baseline used for correctness comparison.
    """
    normalized_prefix = _normalize(prefix)

    if not normalized_prefix:
        return []

    record_tuple = tuple(records)
    return _search_candidate_ids(
        normalized_prefix,
        record_tuple,
        range(len(record_tuple)),
    )


def _search_candidate_ids(
    normalized_prefix: str,
    records: Iterable[SentenceRecord],
    record_ids: Iterable[int],
) -> list[AutoCompleteData]:
    record_tuple = records if isinstance(records, tuple) else tuple(records)
    results: list[AutoCompleteData] = []
    seen_record_ids: set[int] = set()
    for record_id in record_ids:
        if record_id in seen_record_ids:
            continue
        seen_record_ids.add(record_id)
        record = record_tuple[record_id]
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

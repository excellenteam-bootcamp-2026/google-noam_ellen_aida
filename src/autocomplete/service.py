"""Integration layer for autocomplete initialization and querying."""

import time
from collections.abc import Iterable
from pathlib import Path

import heapq

from .models import AutoCompleteData, SentenceRecord

_records: list[SentenceRecord] | None = None


def _load_index(index_path: Path) -> Iterable[SentenceRecord]:
    """Load the index through the data/index component."""

    from .index import load_index

    return load_index(index_path).records


def _normalize(text: str) -> str:
    """Normalize text through the shared normalization component."""

    from .normalization import normalize_text

    return normalize_text(text)


def _find_best_match_score(prefix: str, sentence: str) -> int | None:
    """Score a sentence through the matching component."""

    from .matcher import find_best_match_score

    return find_best_match_score(prefix, sentence)


def _reset_matcher_timing() -> None:
    """Reset the matcher's per-phase timing totals through the matching component."""

    from .matcher import reset_timing

    reset_timing()


def _print_matcher_timing() -> None:
    """Print the matcher's per-phase timing totals through the matching component."""

    from .matcher import print_timing

    print_timing()


def initialize(index_path: Path) -> None:
    """Load the prepared sentence index used by subsequent queries."""

    if not index_path.is_file():
        raise FileNotFoundError(f"Prepared index not found: {index_path}")

    load_start_time = time.perf_counter()
    loaded_records = list(_load_index(index_path))
    load_elapsed_seconds = time.perf_counter() - load_start_time
    print(f"_load_index took {load_elapsed_seconds:.4f} sec")
    if not all(isinstance(record, SentenceRecord) for record in loaded_records):
        raise TypeError("The prepared index must contain SentenceRecord objects")

    global _records
    _records = loaded_records


def get_best_k_completions(prefix: str) -> list[AutoCompleteData]:
    """Return the five highest-ranked completions for ``prefix``."""

    if _records is None:
        raise RuntimeError("Autocomplete service has not been initialized")

    return search_records(prefix, _records)


def search_records(
    prefix: str,
    records: Iterable[SentenceRecord],
) -> list[AutoCompleteData]:
    """Return the five highest-ranked completions from loaded records.

    Every record is checked so that the final results are guaranteed to be the
    best five. A size-five heap is used so all matching results do not need to
    be stored and sorted together.
    """
    normalized_prefix = _normalize(prefix)

    if not normalized_prefix:
        return []

    def matching_results() -> Iterable[AutoCompleteData]:
        """Generate matching results one at a time."""
        for record in records:
            score = _find_best_match_score(
                normalized_prefix,
                record.normalized_text,
            )

            if score is None:
                continue

            yield AutoCompleteData(
    start_time = time.perf_counter()

    normalize_start_time = time.perf_counter()
    normalized_prefix = _normalize(prefix)
    normalize_elapsed_seconds = time.perf_counter() - normalize_start_time
    print(f"_normalize took {normalize_elapsed_seconds:.4f} sec")
    if not normalized_prefix:
        return []

    _reset_matcher_timing()

    results: list[AutoCompleteData] = []
    matching_elapsed_seconds = 0.0
    for record in _records:
        matching_start_time = time.perf_counter()
        score = _find_best_match_score(
            normalized_prefix,
            record.normalized_text,
        )
        matching_elapsed_seconds += time.perf_counter() - matching_start_time
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
    print(f"_find_best_match_score took {matching_elapsed_seconds:.4f} sec total")
    _print_matcher_timing()

    return heapq.nsmallest(
        5,
        matching_results(),
        key=lambda result: (
            -result.score,
            result.completed_sentence.casefold(),
            result.source_text.casefold(),
            result.offset,
        ),
    )

    elapsed_seconds = time.perf_counter() - start_time
    print(f"Records checked: {len(_records):,}")
    print(f"Matching records: {len(results):,}")
    print(f"Search took {elapsed_seconds:.4f} sec")
    return results[:5]

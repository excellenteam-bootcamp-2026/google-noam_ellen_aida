"""Character n-gram candidate generation for autocomplete indexes."""

from __future__ import annotations

from array import array
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from autocomplete.matcher import find_best_match_score
from autocomplete.models import NGramInvertedIndex, SentenceRecord
from autocomplete.normalization import normalize_text

DEFAULT_NGRAM_SIZES = (2, 3)
MIN_INDEXED_QUERY_LENGTH = 4


@dataclass(frozen=True, slots=True)
class CandidateDiagnostics:
    query: str
    total_records: int
    candidate_records: int
    candidate_percentage: float
    canonical_matching_records: int
    candidate_recall: float | None
    false_negatives: int
    false_positives: int
    verified_matches: int
    final_results: int
    used_full_scan: bool


def build_ngram_index(
    records: Sequence[SentenceRecord],
    *,
    ngram_sizes: tuple[int, ...] = DEFAULT_NGRAM_SIZES,
    min_query_length: int = MIN_INDEXED_QUERY_LENGTH,
) -> NGramInvertedIndex:
    """Build deterministic record-id postings for each distinct record n-gram."""

    mutable: dict[int, defaultdict[str, array]] = {
        size: defaultdict(lambda: array("I")) for size in ngram_sizes
    }
    for record_id, record in enumerate(records):
        text = record.normalized_text
        for size in ngram_sizes:
            if len(text) < size:
                continue
            for gram in sorted(set(_iter_ngrams(text, size))):
                mutable[size][gram].append(record_id)

    postings = {
        size: dict(sorted(size_postings.items()))
        for size, size_postings in mutable.items()
    }
    return NGramInvertedIndex(
        ngram_sizes=tuple(sorted(ngram_sizes)),
        min_query_length=min_query_length,
        postings=postings,
    )


def candidate_record_ids(
    normalized_query: str,
    records: Sequence[SentenceRecord],
    ngram_index: NGramInvertedIndex | None,
) -> tuple[int, ...]:
    """Return recall-safe candidate record IDs in deterministic order."""

    if not normalized_query:
        return ()
    if ngram_index is None or len(normalized_query) < MIN_INDEXED_QUERY_LENGTH:
        return tuple(range(len(records)))

    candidate_ids: set[int] = set()
    for anchor in _safe_query_anchors(normalized_query):
        candidate_ids.update(_records_containing_exact_piece(anchor, ngram_index))

    return tuple(
        sorted(record_id for record_id in candidate_ids if record_id < len(records))
    )


def uses_full_scan(
    normalized_query: str,
    ngram_index: NGramInvertedIndex | None,
) -> bool:
    return bool(normalized_query) and (
        ngram_index is None or len(normalized_query) < MIN_INDEXED_QUERY_LENGTH
    )


def measure_candidate_recall(
    query: str,
    records: Sequence[SentenceRecord],
    ngram_index: NGramInvertedIndex | None,
    *,
    final_result_count: int,
) -> CandidateDiagnostics:
    """Compare generated candidates against all canonical matching record IDs."""

    normalized_query = normalize_text(query)
    candidates = set(candidate_record_ids(normalized_query, records, ngram_index))
    canonical_matches = {
        record_id
        for record_id, record in enumerate(records)
        if find_best_match_score(normalized_query, record.normalized_text) is not None
    }
    false_negatives = canonical_matches.difference(candidates)
    false_positives = candidates.difference(canonical_matches)
    recall = None
    if canonical_matches:
        recall = (
            len(canonical_matches) - len(false_negatives)
        ) / len(canonical_matches)

    total_records = len(records)
    candidate_count = len(candidates)
    return CandidateDiagnostics(
        query=query,
        total_records=total_records,
        candidate_records=candidate_count,
        candidate_percentage=(
            candidate_count / total_records * 100 if total_records else 0.0
        ),
        canonical_matching_records=len(canonical_matches),
        candidate_recall=recall,
        false_negatives=len(false_negatives),
        false_positives=len(false_positives),
        verified_matches=len(canonical_matches),
        final_results=final_result_count,
        used_full_scan=uses_full_scan(normalized_query, ngram_index),
    )


def _safe_query_anchors(query: str) -> tuple[str, str]:
    middle = len(query) // 2
    return query[:middle], query[middle:]


def _records_containing_exact_piece(
    piece: str,
    ngram_index: NGramInvertedIndex,
) -> set[int]:
    if not piece:
        return set()

    size = min(3, len(piece))
    if size not in ngram_index.postings:
        return set()

    if len(piece) < 3:
        return set(ngram_index.postings[size].get(piece, ()))

    grams = sorted(
        set(_iter_ngrams(piece, size)),
        key=lambda gram: len(ngram_index.postings[size].get(gram, ())),
    )
    if not grams:
        return set()

    postings = ngram_index.postings[size]
    candidates = set(postings.get(grams[0], ()))
    for gram in grams[1:]:
        candidates.intersection_update(postings.get(gram, ()))
        if not candidates:
            break
    return candidates


def _iter_ngrams(text: str, size: int) -> Iterable[str]:
    for start in range(len(text) - size + 1):
        yield text[start : start + size]

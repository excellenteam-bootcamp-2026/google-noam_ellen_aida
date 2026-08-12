"""Simple correctness oracle for autocomplete tests.

This module intentionally does not import the production matcher or service. It
uses only shared data models and normalization, then scans every record and every
alignment directly.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from autocomplete.models import AutoCompleteData, SentenceRecord
from autocomplete.normalization import normalize_text


_REPLACEMENT_PENALTIES = (5, 4, 3, 2)
_LENGTH_EDIT_PENALTIES = (10, 8, 6, 4)


@dataclass(frozen=True)
class LinearAlignment:
    """One valid alignment between a normalized query and sentence window."""

    edit_type: str
    edit_position: int | None
    matching_letters: int
    score: int


def linear_autocomplete(
    query: str,
    records: Iterable[SentenceRecord],
    *,
    limit: int = 5,
) -> list[AutoCompleteData]:
    """Return top autocomplete results from a deliberate full linear scan."""

    normalized_query = normalize_text(query)
    if not normalized_query:
        return []

    results: list[AutoCompleteData] = []
    for record in records:
        score = find_best_linear_match_score(normalized_query, record.normalized_text)
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
    return results[:limit]


def find_best_linear_match_score(
    normalized_query: str,
    normalized_sentence: str,
) -> int | None:
    """Return the best score for one normalized sentence, or ``None``."""

    if not normalized_query:
        return None

    scores = [
        alignment.score
        for alignment in iter_linear_alignments(normalized_query, normalized_sentence)
    ]
    if not scores:
        return None
    return max(scores)


def iter_linear_alignments(
    normalized_query: str,
    normalized_sentence: str,
) -> Iterator[LinearAlignment]:
    """Yield every exact or one-edit alignment found by direct verification."""

    if not normalized_query:
        return

    query_length = len(normalized_query)
    for window_length in (query_length, query_length - 1, query_length + 1):
        if window_length < 0:
            continue
        for start in _valid_starts(normalized_sentence, window_length):
            window = normalized_sentence[start : start + window_length]
            yield from score_window(normalized_query, window)


def score_window(normalized_query: str, window: str) -> Iterator[LinearAlignment]:
    """Yield valid match interpretations for a single sentence window."""

    query_length = len(normalized_query)
    window_length = len(window)

    if query_length == window_length:
        if normalized_query == window:
            yield LinearAlignment("exact", None, query_length, 2 * query_length)
            return

        differences = [
            index
            for index, (query_char, window_char) in enumerate(zip(normalized_query, window))
            if query_char != window_char
        ]
        if len(differences) == 1:
            position = differences[0]
            yield LinearAlignment(
                "replacement",
                position,
                query_length,
                2 * query_length - _replacement_penalty(position),
            )
        return

    if query_length == window_length + 1:
        for position in range(query_length):
            if normalized_query[:position] + normalized_query[position + 1 :] == window:
                yield LinearAlignment(
                    "extra_query_character",
                    position,
                    window_length,
                    2 * window_length - _length_edit_penalty(position),
                )
        return

    if window_length == query_length + 1:
        for position in range(window_length):
            if window[:position] + window[position + 1 :] == normalized_query:
                yield LinearAlignment(
                    "missing_query_character",
                    position,
                    query_length,
                    2 * query_length - _length_edit_penalty(position),
                )


def _valid_starts(sentence: str, window_length: int) -> range:
    if window_length > len(sentence):
        return range(0)
    return range(len(sentence) - window_length + 1)


def _replacement_penalty(position: int) -> int:
    if position < len(_REPLACEMENT_PENALTIES):
        return _REPLACEMENT_PENALTIES[position]
    return 1


def _length_edit_penalty(position: int) -> int:
    if position < len(_LENGTH_EDIT_PENALTIES):
        return _LENGTH_EDIT_PENALTIES[position]
    return 2

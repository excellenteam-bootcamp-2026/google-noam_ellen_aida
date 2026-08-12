"""Deterministic comparison helpers for autocomplete implementations."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import PurePath
from typing import Literal

from autocomplete.models import AutoCompleteData, SentenceRecord

MismatchCategory = Literal[
    "missing_result",
    "unexpected_result",
    "score_mismatch",
    "metadata_mismatch",
    "ordering_mismatch",
    "count_mismatch",
    "top_five_mismatch",
    "exception",
]
SearchFunction = Callable[[str, Iterable[SentenceRecord]], list[AutoCompleteData]]


@dataclass(frozen=True)
class CanonicalResult:
    completed_sentence: str
    score: int
    source_text: str
    offset: int


@dataclass(frozen=True)
class ComparisonMismatch:
    query: str
    category: MismatchCategory
    oracle_output: tuple[CanonicalResult, ...]
    production_output: tuple[CanonicalResult, ...]
    differing_fields: tuple[str, ...]
    likely_responsible_layer: str


@dataclass(frozen=True)
class QueryComparison:
    query: str
    passed: bool
    mismatches: tuple[ComparisonMismatch, ...] = ()


@dataclass(frozen=True)
class ComparisonSummary:
    total_queries: int
    passed_queries: int
    failed_queries: int
    mismatches: tuple[ComparisonMismatch, ...] = ()
    exceptions: tuple[ComparisonMismatch, ...] = ()

    @property
    def agreement_percentage(self) -> float:
        if self.total_queries == 0:
            return 100.0
        return self.passed_queries / self.total_queries * 100

    @property
    def mismatch_counts(self) -> dict[MismatchCategory, int]:
        counts: Counter[MismatchCategory] = Counter()
        for mismatch in (*self.mismatches, *self.exceptions):
            counts[mismatch.category] += 1
        return dict(counts)

    @property
    def exit_code(self) -> int:
        return 0 if self.failed_queries == 0 else 1


@dataclass
class ComparisonRunner:
    records: Sequence[SentenceRecord]
    queries: Sequence[str]
    oracle_search: SearchFunction
    production_search: SearchFunction

    def run(self) -> ComparisonSummary:
        comparisons: list[QueryComparison] = []
        exceptions: list[ComparisonMismatch] = []

        for query in self.queries:
            try:
                oracle_results = self.oracle_search(query, self.records)
                production_results = self.production_search(query, self.records)
            except Exception as error:
                # Comparison must report unexpected failures instead of hiding them.
                exception = _exception_mismatch(query, error)
                exceptions.append(exception)
                comparisons.append(QueryComparison(query, False, (exception,)))
                continue

            comparison = compare_result_lists(query, oracle_results, production_results)
            comparisons.append(comparison)

        mismatches = tuple(
            mismatch
            for comparison in comparisons
            for mismatch in comparison.mismatches
            if mismatch.category != "exception"
        )
        passed_queries = sum(1 for comparison in comparisons if comparison.passed)
        return ComparisonSummary(
            total_queries=len(self.queries),
            passed_queries=passed_queries,
            failed_queries=len(self.queries) - passed_queries,
            mismatches=mismatches,
            exceptions=tuple(exceptions),
        )


def compare_result_lists(
    query: str,
    oracle_results: Sequence[AutoCompleteData],
    production_results: Sequence[AutoCompleteData],
) -> QueryComparison:
    oracle_output = canonicalize_results(oracle_results)
    production_output = canonicalize_results(production_results)
    if oracle_output == production_output:
        return QueryComparison(query, True)

    mismatch = ComparisonMismatch(
        query=query,
        category=_classify_mismatch(oracle_output, production_output),
        oracle_output=oracle_output,
        production_output=production_output,
        differing_fields=_differing_fields(oracle_output, production_output),
        likely_responsible_layer=_likely_responsible_layer(
            _differing_fields(oracle_output, production_output)
        ),
    )
    return QueryComparison(query, False, (mismatch,))


def canonicalize_results(
    results: Sequence[AutoCompleteData],
) -> tuple[CanonicalResult, ...]:
    return tuple(
        CanonicalResult(
            completed_sentence=result.completed_sentence,
            score=result.score,
            source_text=_normalize_source_path(result.source_text),
            offset=result.offset,
        )
        for result in results
    )


def _normalize_source_path(source_path: str) -> str:
    return PurePath(source_path).as_posix()


def _classify_mismatch(
    oracle_output: tuple[CanonicalResult, ...],
    production_output: tuple[CanonicalResult, ...],
) -> MismatchCategory:
    if len(oracle_output) != len(production_output):
        if not production_output:
            return "missing_result"
        if not oracle_output:
            return "unexpected_result"
        return "count_mismatch"
    if Counter(oracle_output) == Counter(production_output):
        return "ordering_mismatch"

    differing_fields = _differing_fields(oracle_output, production_output)
    if "score" in differing_fields:
        return "score_mismatch"
    if {"source_text", "offset"} & set(differing_fields):
        return "metadata_mismatch"
    if len(oracle_output) == 5 and Counter(oracle_output) != Counter(production_output):
        return "top_five_mismatch"
    if _has_missing_result(oracle_output, production_output):
        return "missing_result"
    if _has_unexpected_result(oracle_output, production_output):
        return "unexpected_result"
    return "ordering_mismatch"


def _has_missing_result(
    oracle_output: tuple[CanonicalResult, ...],
    production_output: tuple[CanonicalResult, ...],
) -> bool:
    oracle_counts = Counter(oracle_output)
    production_counts = Counter(production_output)
    return any(production_counts[result] < count for result, count in oracle_counts.items())


def _has_unexpected_result(
    oracle_output: tuple[CanonicalResult, ...],
    production_output: tuple[CanonicalResult, ...],
) -> bool:
    oracle_counts = Counter(oracle_output)
    production_counts = Counter(production_output)
    return any(oracle_counts[result] < count for result, count in production_counts.items())


def _differing_fields(
    oracle_output: tuple[CanonicalResult, ...],
    production_output: tuple[CanonicalResult, ...],
) -> tuple[str, ...]:
    fields: set[str] = set()
    for oracle_result, production_result in zip(oracle_output, production_output):
        if oracle_result.completed_sentence != production_result.completed_sentence:
            fields.add("completed_sentence")
        if oracle_result.score != production_result.score:
            fields.add("score")
        if oracle_result.source_text != production_result.source_text:
            fields.add("source_text")
        if oracle_result.offset != production_result.offset:
            fields.add("offset")
    if len(oracle_output) != len(production_output):
        fields.add("result_count")
    return tuple(sorted(fields))


def _likely_responsible_layer(differing_fields: tuple[str, ...]) -> str:
    field_set = set(differing_fields)
    if "score" in field_set:
        return "matching/scoring"
    if {"source_text", "offset"} & field_set:
        return "metadata construction"
    if "completed_sentence" in field_set:
        return "matching/ranking"
    if "result_count" in field_set:
        return "matching/top-five selection"
    return "ordering"


def _exception_mismatch(query: str, error: Exception) -> ComparisonMismatch:
    return ComparisonMismatch(
        query=query,
        category="exception",
        oracle_output=(),
        production_output=(),
        differing_fields=(type(error).__name__, str(error)),
        likely_responsible_layer="unexpected exception",
    )

"""Benchmark canonical linear search against n-gram candidate search."""

from __future__ import annotations

from argparse import ArgumentParser
from contextlib import redirect_stdout
from dataclasses import asdict, dataclass
from io import StringIO
import json
from pathlib import Path
import signal
import sys
from time import perf_counter, perf_counter_ns

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autocomplete.index import build_index, load_index
from autocomplete.loader import load_sentence_records
from autocomplete.ngram import candidate_record_ids, measure_candidate_recall
from autocomplete.normalization import normalize_text
from autocomplete.service import search_index, search_records

DEFAULT_INDEX = PROJECT_ROOT / "data" / "prepared" / "autocomplete-index.json"
DEFAULT_QUERIES = (
    "alpha",
    "HELLO WORLD",
    "omega",
    "wprd",
    "wrd",
    "wordx",
    "wordd",
    "woord",
    "aaa",
    "ab",
    "aa",
    "aab",
    "no-such-query",
    "hi",
    "python",
    "network",
    "database",
    "security",
    "function",
    "authentication",
    "word",
    "missing",
    "query",
    "A",
    "to",
    "be",
)


@dataclass(frozen=True)
class QueryTiming:
    query: str
    query_length: int
    total_records: int
    candidates: int
    candidate_percentage: float
    canonical_matches: int | None
    recall: float | None
    false_negatives: int | None
    baseline_p50_ms: float | None
    optimized_p50_ms: float
    baseline_p95_ms: float | None
    optimized_p95_ms: float
    speedup: float | None
    full_scan_fallback: bool
    baseline_status: str


class TimeoutExpired(Exception):
    pass


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--query", action="append", dest="queries")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--limit-records", type=int)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    queries = tuple(args.queries) if args.queries is not None else DEFAULT_QUERIES

    load_start = perf_counter()
    if args.corpus is not None:
        records = tuple(load_sentence_records(args.corpus))
        if args.limit_records is not None:
            records = records[: args.limit_records]
        build_start = perf_counter()
        prepared = build_index(records)
        build_seconds = perf_counter() - build_start
    else:
        prepared = load_index(args.index)
        if args.limit_records is not None:
            prepared = build_index(prepared.records[: args.limit_records])
        build_seconds = None
    load_seconds = perf_counter() - load_start

    rows = [
        benchmark_query(
            query,
            prepared,
            warmup=args.warmup,
            repeat=args.repeat,
            timeout=args.timeout,
        )
        for query in queries
    ]
    report = {
        "index": str(args.index),
        "corpus": str(args.corpus) if args.corpus else None,
        "record_count": len(prepared.records),
        "load_seconds": load_seconds,
        "build_seconds": build_seconds,
        "queries": [asdict(row) for row in rows],
    }

    print(json.dumps(report, indent=2, sort_keys=True))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


def benchmark_query(
    query: str,
    prepared,
    *,
    warmup: int,
    repeat: int,
    timeout: int,
) -> QueryTiming:
    normalized_query = normalize_text(query)
    candidates = candidate_record_ids(
        normalized_query,
        prepared.records,
        prepared.ngram_index,
    )
    for _ in range(warmup):
        search_index(query, prepared)

    optimized_times = [
        _time_call(lambda: search_index(query, prepared))
        for _ in range(repeat)
    ]
    baseline_times: list[float] = []
    baseline_status = "ok"
    for _ in range(repeat):
        try:
            baseline_times.append(
                _time_with_timeout(
                    lambda: search_records(query, prepared.records),
                    timeout=timeout,
                )
            )
        except TimeoutExpired:
            baseline_status = f"timeout>{timeout}s"
            break

    diagnostics = None
    if baseline_status == "ok":
        diagnostics = measure_candidate_recall(
            query,
            prepared.records,
            prepared.ngram_index,
            final_result_count=len(search_index(query, prepared)),
        )

    baseline_p50 = _percentile(baseline_times, 50) if baseline_times else None
    optimized_p50 = _percentile(optimized_times, 50)
    return QueryTiming(
        query=query,
        query_length=len(normalized_query),
        total_records=len(prepared.records),
        candidates=len(candidates),
        candidate_percentage=(
            len(candidates) / len(prepared.records) * 100 if prepared.records else 0.0
        ),
        canonical_matches=(
            diagnostics.canonical_matching_records if diagnostics is not None else None
        ),
        recall=diagnostics.candidate_recall if diagnostics is not None else None,
        false_negatives=(
            diagnostics.false_negatives if diagnostics is not None else None
        ),
        baseline_p50_ms=baseline_p50,
        optimized_p50_ms=optimized_p50,
        baseline_p95_ms=_percentile(baseline_times, 95) if baseline_times else None,
        optimized_p95_ms=_percentile(optimized_times, 95),
        speedup=(baseline_p50 / optimized_p50) if baseline_p50 is not None else None,
        full_scan_fallback=len(candidates) == len(prepared.records)
        and bool(normalized_query),
        baseline_status=baseline_status,
    )


def _time_call(callback) -> float:
    start = perf_counter_ns()
    callback()
    return (perf_counter_ns() - start) / 1_000_000


def _time_with_timeout(callback, *, timeout: int) -> float:
    def handle_timeout(_signum, _frame):
        raise TimeoutExpired()

    previous = signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(timeout)
    try:
        with redirect_stdout(StringIO()):
            return _time_call(callback)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    index = round((percentile / 100) * (len(ordered) - 1))
    return ordered[index]


if __name__ == "__main__":
    raise SystemExit(main())

"""Profile the correct Python Part A implementation on a deterministic fixture."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from statistics import mean, median
from tempfile import TemporaryDirectory
from time import perf_counter
import platform
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
TESTS_ROOT = PROJECT_ROOT / "tests"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from autocomplete.comparison import ComparisonRunner
from autocomplete.index import build_index, load_index, save_index
from autocomplete.loader import iter_text_files, load_sentence_records
from autocomplete.normalization import normalize_text
from autocomplete.service import search_records
from reference_oracle import linear_autocomplete

DEFAULT_FIXTURE = TESTS_ROOT / "fixtures" / "reference_oracle"
DEFAULT_QUERIES = (
    "alpha",
    "HELLO WORLD",
    "omega",
    "wprd",
    "wrd",
    "wordd",
    "woord",
    "aaa",
    "ab",
    "aa",
    "aab",
    "no-such-query",
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Profile Python Part A autocomplete.")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="small deterministic corpus path; defaults to the reference fixture",
    )
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="query to profile; may be repeated; defaults to deterministic fixture queries",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=50,
        help="warm query repetitions per query",
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    queries = tuple(arguments.queries) if arguments.queries is not None else DEFAULT_QUERIES

    discovery_start = perf_counter()
    files = tuple(iter_text_files(arguments.corpus))
    discovery_seconds = perf_counter() - discovery_start
    corpus_bytes = sum(path.stat().st_size for path in files)

    loading_start = perf_counter()
    records = tuple(load_sentence_records(arguments.corpus))
    loading_seconds = perf_counter() - loading_start
    corpus_characters = sum(len(record.original_text) for record in records)

    comparison = ComparisonRunner(
        records=records,
        queries=queries,
        oracle_search=linear_autocomplete,
        production_search=search_records,
    ).run()
    if comparison.exit_code != 0:
        print("Refusing to profile: production does not match oracle.")
        print(f"agreement: {comparison.agreement_percentage:.2f}%")
        return comparison.exit_code

    normalization_start = perf_counter()
    for record in records:
        normalize_text(record.original_text)
    normalization_seconds = perf_counter() - normalization_start

    build_start = perf_counter()
    prepared = build_index(records)
    build_seconds = perf_counter() - build_start

    with TemporaryDirectory() as temp_dir:
        index_path = Path(temp_dir) / "index.json"

        save_start = perf_counter()
        save_index(prepared, index_path)
        save_seconds = perf_counter() - save_start
        index_size = index_path.stat().st_size

        load_start = perf_counter()
        loaded_records = load_index(index_path).records
        load_seconds = perf_counter() - load_start

    query_seconds: list[float] = []
    cold_query_seconds: list[float] = []

    for query in queries:
        cold_start = perf_counter()
        search_records(query, loaded_records)
        cold_query_seconds.append(perf_counter() - cold_start)

        for _ in range(arguments.repeat):
            query_start = perf_counter()
            search_records(query, loaded_records)
            query_seconds.append(perf_counter() - query_start)

    print(f"python: {platform.python_version()} ({platform.python_implementation()})")
    print(f"platform: {platform.platform()}")
    print(f"corpus path: {arguments.corpus}")
    print(f"files: {len(files)}")
    print(f"records: {len(records)}")
    print(f"corpus bytes: {corpus_bytes}")
    print(f"corpus characters: {corpus_characters}")
    print(f"queries: {len(queries)}")
    print(f"query lengths: {[len(query) for query in queries]}")
    print(f"oracle agreement: {comparison.agreement_percentage:.2f}%")
    print(f"discovery seconds: {discovery_seconds:.6f}")
    print(f"loading seconds: {loading_seconds:.6f}")
    print(f"normalization seconds: {normalization_seconds:.6f}")
    print(f"index build seconds: {build_seconds:.6f}")
    print(f"index save seconds: {save_seconds:.6f}")
    print(f"index load seconds: {load_seconds:.6f}")
    print(f"serialized index bytes: {index_size}")
    print(f"cold query mean seconds: {mean(cold_query_seconds):.6f}")
    print(f"warm query mean seconds: {mean(query_seconds):.6f}")
    print(f"warm query p50 seconds: {median(query_seconds):.6f}")
    print(f"warm query p95 seconds: {_percentile(query_seconds, 95):.6f}")
    print(f"warm query min seconds: {min(query_seconds):.6f}")
    print(f"warm query max seconds: {max(query_seconds):.6f}")
    print("confirmed bottleneck: not established on this small fixture")
    return 0


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    index = round((percentile / 100) * (len(ordered) - 1))
    return ordered[index]


if __name__ == "__main__":
    raise SystemExit(main())

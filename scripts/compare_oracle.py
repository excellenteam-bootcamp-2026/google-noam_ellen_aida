"""Compare production autocomplete output with the linear oracle on fixtures."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
TESTS_ROOT = PROJECT_ROOT / "tests"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from autocomplete.comparison import ComparisonRunner
from autocomplete.loader import load_sentence_records
from autocomplete.service import search_records
from reference_oracle import linear_autocomplete

DEFAULT_FIXTURE = TESTS_ROOT / "fixtures" / "reference_oracle"
DEFAULT_QUERIES = (
    "",
    "?!",
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
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Compare production autocomplete results with the linear oracle."
    )
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
        help="query to compare; may be repeated; defaults to a deterministic fixture set",
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    queries = tuple(arguments.queries) if arguments.queries is not None else DEFAULT_QUERIES
    records = tuple(load_sentence_records(arguments.corpus))

    summary = ComparisonRunner(
        records=records,
        queries=queries,
        oracle_search=linear_autocomplete,
        production_search=search_records,
    ).run()

    print(f"records: {len(records)}")
    print(f"total queries: {summary.total_queries}")
    print(f"passed queries: {summary.passed_queries}")
    print(f"failed queries: {summary.failed_queries}")
    print(f"agreement: {summary.agreement_percentage:.2f}%")
    print(f"mismatch counts: {summary.mismatch_counts}")

    for mismatch in (*summary.mismatches, *summary.exceptions):
        print()
        print(f"Query: {mismatch.query!r}")
        print(f"Oracle output: {mismatch.oracle_output}")
        print(f"Production output: {mismatch.production_output}")
        print(f"Differing fields: {mismatch.differing_fields}")
        print(f"Mismatch category: {mismatch.category}")
        print(f"Likely responsible layer: {mismatch.likely_responsible_layer}")

    return summary.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

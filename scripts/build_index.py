"""Build a prepared autocomplete index from raw text files."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autocomplete.index import build_index, save_index
from autocomplete.loader import load_sentence_records


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Build a prepared autocomplete index.")
    parser.add_argument(
        "corpus_path",
        type=Path,
        help="raw .txt file or directory to index",
    )
    parser.add_argument(
        "index_path",
        type=Path,
        help="output prepared index path",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    load_start = perf_counter()
    records = load_sentence_records(args.corpus_path)
    load_seconds = perf_counter() - load_start

    build_start = perf_counter()
    prepared = build_index(records)
    build_seconds = perf_counter() - build_start

    save_start = perf_counter()
    save_index(prepared, args.index_path)
    save_seconds = perf_counter() - save_start

    print(f"records: {len(records):,}")
    print(f"load seconds: {load_seconds:.3f}")
    print(f"build seconds: {build_seconds:.3f}")
    print(f"save seconds: {save_seconds:.3f}")
    print(f"index bytes: {args.index_path.stat().st_size:,}")
    print(f"wrote: {args.index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

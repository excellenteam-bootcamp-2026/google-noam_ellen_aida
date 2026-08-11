"""Start the online autocomplete service from a prepared index."""

from argparse import ArgumentParser
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from autocomplete.cli import run_cli
from autocomplete.service import initialize


def build_parser() -> ArgumentParser:
    """Create the command-line argument parser."""

    parser = ArgumentParser(description="Run sentence autocomplete")
    parser.add_argument(
        "index_path",
        type=Path,
        help="path to the prepared sentence index",
    )
    return parser


def main() -> int:
    """Initialize the service and start its interactive interface."""

    arguments = build_parser().parse_args()

    try:
        initialize(arguments.index_path)
    except (FileNotFoundError, TypeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    run_cli()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line interface for the sentence autocomplete service."""

from .models import AutoCompleteData
from .service import get_best_k_completions


def format_completion(result: AutoCompleteData) -> str:
    """Format one completion for display without changing its data."""

    return (
        f"{result.completed_sentence} "
        f"({result.source_text}:{result.offset}) "
        f"[score: {result.score}]"
    )


def display_completions(results: list[AutoCompleteData]) -> None:
    """Print a numbered completion list or a no-results message."""

    if not results:
        print("No completions found.")
        return

    for position, result in enumerate(results, start=1):
        print(f"{position}. {format_completion(result)}")


def run_cli() -> None:
    """Run the interactive input, continuation, and reset loop."""

    current_prefix = ""

    while True:
        try:
            entered_text = input("Enter text (# to reset): ")
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if entered_text == "#":
            current_prefix = ""
            print("Query reset.")
            continue

        current_prefix += entered_text

        try:
            results = get_best_k_completions(current_prefix)
        except (FileNotFoundError, RuntimeError, TypeError, ValueError) as error:
            print(f"Error: {error}")
            return

        display_completions(results)

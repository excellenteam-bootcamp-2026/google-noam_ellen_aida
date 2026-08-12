"""Find exact or one-character-error matches inside normalized sentences."""

import time

from autocomplete.models import Match
from autocomplete.scoring import calculate_score

_timing_totals: dict[str, float] = {
    "exact_match": 0.0,
    "candidate_generation": 0.0,
    "substitution": 0.0,
    "insertion": 0.0,
    "deletion": 0.0,
}


def reset_timing() -> None:
    """Reset the accumulated per-phase timing totals."""

    for phase in _timing_totals:
        _timing_totals[phase] = 0.0


def print_timing() -> None:
    """Print the accumulated per-phase timing totals."""

    for phase, total_seconds in _timing_totals.items():
        print(f"matcher.{phase} took {total_seconds:.4f} sec total")


def find_best_match_score(
    normalized_prefix: str,
    normalized_sentence: str,
) -> int | None:
    """Return the best score for the query inside the sentence.

    The matcher supports:

    - Exact matching
    - One substituted character
    - One extra character in the query
    - One missing character from the query

    Exact matches use Python's fast substring search. Approximate matches use
    anchors to locate likely starting positions, followed by two-pointer
    verification.
    """
    if not normalized_prefix or not normalized_sentence:
        return None

    # A query can be at most one character longer than its matching sentence
    # window. If it is longer than the entire sentence by more than one
    # character, no supported match is possible.
    if len(normalized_prefix) > len(normalized_sentence) + 1:
        return None

    # Fast path: Python performs this substring search in optimized code.
    exact_start_time = time.perf_counter()
    is_exact_match = normalized_prefix in normalized_sentence
    _timing_totals["exact_match"] += time.perf_counter() - exact_start_time

    if is_exact_match:
        exact_match = Match(
            edit_type="exact",
            edit_position=None,
            matching_letters=len(normalized_prefix),
        )
        return calculate_score(exact_match)

    candidates_start_time = time.perf_counter()
    candidate_starts = _find_candidate_starts(
        normalized_prefix,
        normalized_sentence,
    )
    _timing_totals["candidate_generation"] += time.perf_counter() - candidates_start_time

    best_score: int | None = None

    for position in candidate_starts:
        substitution_start_time = time.perf_counter()
        substitution_result = _try_substitution_at(
            normalized_prefix,
            normalized_sentence,
            position,
        )
        _timing_totals["substitution"] += time.perf_counter() - substitution_start_time

        insertion_start_time = time.perf_counter()
        insertion_result = _try_insertion_at(
            normalized_prefix,
            normalized_sentence,
            position,
        )
        _timing_totals["insertion"] += time.perf_counter() - insertion_start_time

        deletion_start_time = time.perf_counter()
        deletion_result = _try_deletion_at(
            normalized_prefix,
            normalized_sentence,
            position,
        )
        _timing_totals["deletion"] += time.perf_counter() - deletion_start_time

        for match_result in (substitution_result, insertion_result, deletion_result):
            if match_result is None:
                continue

            score = calculate_score(match_result)

            if best_score is None or score > best_score:
                best_score = score

    return best_score


def _find_candidate_starts(query: str, sentence: str) -> set[int]:
    """Find likely match starts using two unchanged query anchors.

    A match may contain no more than one changed, inserted, or deleted
    character. Splitting the query into two anchors means at least one anchor
    should remain unchanged.

    An insertion or deletion can shift an anchor by one position, so each
    anchor occurrence creates three possible starts.
    """
    if not query or not sentence:
        return set()

    # Anchor searching is not useful for very short queries. Checking every
    # sentence position is inexpensive in this case and avoids empty or
    # one-character anchors.
   # if len(query) < 2:
   #     return set(range(len(sentence)))

    middle = len(query) // 2

    anchors = (
        (query[:middle], 0),
        (query[middle:], middle),
    )

    candidate_starts: set[int] = set()

    for anchor, query_offset in anchors:
        search_from = 0

        while True:
            occurrence = sentence.find(anchor, search_from)

            if occurrence == -1:
                break

            expected_start = occurrence - query_offset

            # No shift: substitution or exact alignment.
            # Shift by one: insertion or deletion before the anchor.
            for shift in (-1, 0, 1):
                candidate_start = expected_start + shift

                if 0 <= candidate_start < len(sentence):
                    candidate_starts.add(candidate_start)

            # Move by one so overlapping anchor occurrences are also found.
            search_from = occurrence + 1

    return candidate_starts


def _try_exact_match_at(
    query: str,
    sentence: str,
    pos: int,
) -> Match | None:
    """Return an exact Match when the query starts at the given position."""
    if not query or pos < 0:
        return None

    window = sentence[pos:pos + len(query)]

    if len(window) != len(query):
        return None

    if query == window:
        return Match(
            edit_type="exact",
            edit_position=None,
            matching_letters=len(query),
        )

    return None


def _try_substitution_at(
    query: str,
    sentence: str,
    pos: int,
) -> Match | None:
    """Return a Match when exactly one character is different.

    Query and sentence window must have the same length. The scan stops
    immediately if a second different character is found.
    """
    if not query or pos < 0:
        return None

    window = sentence[pos:pos + len(query)]

    if len(window) != len(query):
        return None

    different_position: int | None = None

    for index, (query_character, sentence_character) in enumerate(
        zip(query, window)
    ):
        if query_character == sentence_character:
            continue

        if different_position is not None:
            return None

        different_position = index

    if different_position is None:
        # This is an exact match, not a substitution.
        return None

    return Match(
        edit_type="substitution",
        edit_position=different_position,
        matching_letters=len(query),
    )


def _try_insertion_at(
    query: str,
    sentence: str,
    pos: int,
) -> Match | None:
    """Return a Match when the query contains one extra character.

    For example:

        query:    helllo
        sentence: hello

    One character must be skipped in the query. The comparison uses prefix and
    suffix pointers instead of creating a new string for every possible skip.
    """
    if len(query) < 2 or pos < 0:
        return None

    expected_window_length = len(query) - 1
    window = sentence[pos:pos + expected_window_length]

    if len(window) != expected_window_length:
        return None

    edit_position = _best_skip_position(
        longer=query,
        shorter=window,
    )

    if edit_position is None:
        return None

    return Match(
        edit_type="insertion",
        edit_position=edit_position,
        matching_letters=len(query) - 1,
    )


def _try_deletion_at(
    query: str,
    sentence: str,
    pos: int,
) -> Match | None:
    """Return a Match when the query is missing one sentence character.

    For example:

        query:    helo
        sentence: hello

    One character must be skipped in the sentence window.
    """
    if not query or pos < 0:
        return None

    expected_window_length = len(query) + 1
    window = sentence[pos:pos + expected_window_length]

    if len(window) != expected_window_length:
        return None

    edit_position = _best_skip_position(
        longer=window,
        shorter=query,
    )

    if edit_position is None:
        return None

    return Match(
        edit_type="deletion",
        edit_position=edit_position,
        matching_letters=len(query),
    )


def _best_skip_position(
    longer: str,
    shorter: str,
) -> int | None:
    """Find the best character position to skip in the longer string.

    The strings must differ in length by exactly one.

    A pointer first counts matching characters from the left. Another pointer
    counts matching characters from the right. Together, those values determine
    whether removing one character can make the strings equal.

    When repeated characters allow more than one valid skip position, the
    latest valid position is returned because later edit positions receive a
    smaller score penalty.
    """
    if len(longer) != len(shorter) + 1:
        return None

    left_matches = 0

    while (
        left_matches < len(shorter)
        and longer[left_matches] == shorter[left_matches]
    ):
        left_matches += 1

    right_matches = 0

    while (
        right_matches < len(shorter)
        and longer[-1 - right_matches] == shorter[-1 - right_matches]
    ):
        right_matches += 1

    first_valid_skip = len(longer) - 1 - right_matches
    last_valid_skip = left_matches

    if first_valid_skip > last_valid_skip:
        return None

    return last_valid_skip

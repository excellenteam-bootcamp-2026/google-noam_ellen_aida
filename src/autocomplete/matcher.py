from autocomplete.models import Match
from autocomplete.scoring import calculate_score


def find_best_match_score(normalized_prefix: str, normalized_sentence: str) -> int | None:
    """Main function - checks all positions and returns best score."""
    if not normalized_prefix:
        return None

    best_score = None
    for position in range(len(normalized_sentence) + 1):
        for match_result in [
            _try_exact_match_at(normalized_prefix, normalized_sentence, position),
            _try_substitution_at(normalized_prefix, normalized_sentence, position),
            _try_insertion_at(normalized_prefix, normalized_sentence, position),
            _try_deletion_at(normalized_prefix, normalized_sentence, position),
        ]:
            if match_result is not None:
                score = calculate_score(match_result)
                best_score = score if best_score is None else max(best_score, score)
    return best_score


def _best_match(matches: list[Match]) -> Match | None:
    if not matches:
        return None
    return max(matches, key=calculate_score)


def _try_exact_match_at(query: str, sentence: str, pos: int) -> Match | None:
    """Check if query matches exactly starting at pos."""
    if query == sentence[pos : pos + len(query)]:
        return Match(edit_type="exact", edit_position=None, matching_letters=len(query))
    return None


def _try_substitution_at(query: str, sentence: str, pos: int) -> Match | None:
    """Check if query matches with one substitution starting at pos."""
    window = sentence[pos : pos + len(query)]

    if len(window) < len(query):
        return None

    differences = []

    for i in range(len(query)):
        if query[i] != window[i]:
            differences.append(i)

    if len(differences) == 1:
        return Match(
            edit_type="substitution",
            edit_position=differences[0],
            matching_letters=len(query),
        )
    return None


def _try_insertion_at(query: str, sentence: str, pos: int) -> Match | None:
    """Check if query matches with one insertion starting at pos."""
    window = sentence[pos : pos + len(query) - 1]

    if len(window) < len(query) - 1:
        return None

    matches = []
    for i in range(len(query)):
        query_without_i = query[:i] + query[i + 1 :]
        if query_without_i == window:
            matches.append(
                Match(
                    edit_type="insertion",
                    edit_position=i,
                    matching_letters=len(query) - 1,
                )
            )
    return _best_match(matches)


def _try_deletion_at(query: str, sentence: str, pos: int) -> Match | None:
    """Check if query matches with one deletion starting at pos."""
    window = sentence[pos : pos + len(query) + 1]

    if len(window) < len(query) + 1:
        return None

    matches = []
    for i in range(len(window)):
        window_without_i = window[:i] + window[i + 1 :]
        if query == window_without_i:
            matches.append(
                Match(
                    edit_type="deletion",
                    edit_position=i,
                    matching_letters=len(query),
                )
            )
    return _best_match(matches)

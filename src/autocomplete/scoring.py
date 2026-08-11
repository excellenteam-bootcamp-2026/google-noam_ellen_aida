from autocomplete.models import Match

def calculate_score(match: Match) -> int:
    """Calculate the score for a match."""
    base_score = 2 * match.query_length

    if match.edit_type == "exact":
        return base_score



    penalty = _get_penalty(match.edit_type, match.edit_position)
    return base_score - penalty



def _get_penalty(edit_type: str, position: int) -> int:
    """Get penalty for an edit at the given position."""

    if edit_type == "substitution":
        match position:
            case 0: return 5
            case 1: return 4
            case 2: return 3
            case 3: return 2
            case _: return 1

    elif edit_type == "insertion" or edit_type == "deletion":
        match position:
            case 0: return 10
            case 1: return 8
            case 2: return 6
            case 3: return 4
            case _: return 2

    return 0
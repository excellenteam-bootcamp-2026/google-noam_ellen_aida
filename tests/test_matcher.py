"""Tests for the matcher module."""

# noinspection PyProtectedMember
from autocomplete.matcher import (
    _try_deletion_at,
    _try_exact_match_at,
    _try_insertion_at,
    _try_substitution_at,
    find_best_match_score,
)


# Exact match tests

def test_exact_match_at_start():
    """Query matches exactly at the start of sentence."""
    result = _try_exact_match_at("to be", "to be or not", 0)
    assert result is not None
    assert result.edit_type == "exact"
    assert result.edit_position is None
    assert result.matching_letters == 5


def test_exact_match_in_middle():
    """Query matches exactly in the middle of sentence."""
    result = _try_exact_match_at("be", "to be or not", 3)
    assert result is not None
    assert result.edit_type == "exact"
    assert result.edit_position is None
    assert result.matching_letters == 2


def test_exact_match_no_match():
    """Query does not match at given position."""
    result = _try_exact_match_at("xyz", "to be or not", 0)
    assert result is None


def test_exact_match_too_short():
    """Not enough characters remaining for query."""
    result = _try_exact_match_at("testing", "to be", 3)
    assert result is None


# Substitution tests

def test_substitution_one_difference():
    """Query with one character different."""
    result = _try_substitution_at("tx be", "to be or not", 0)
    assert result is not None
    assert result.edit_type == "substitution"
    assert result.edit_position == 1  # 'x' vs 'o'
    assert result.matching_letters == 5


def test_substitution_no_differences():
    """Exact match should not be detected as substitution."""
    result = _try_substitution_at("to be", "to be or not", 0)
    assert result is None  # No differences = not a substitution


def test_substitution_multiple_differences():
    """Multiple differences should be rejected."""
    result = _try_substitution_at("xy zw", "to be or not", 0)
    assert result is None  # Too many differences


def test_substitution_at_end():
    """Substitution at last character."""
    result = _try_substitution_at("worx", "the word is", 4)
    assert result is not None
    assert result.edit_type == "substitution"
    assert result.edit_position == 3


# Insertion tests

def test_insertion_extra_char_at_start():
    """Query has extra character at the start."""
    result = _try_insertion_at("xto", "to be or", 0)
    assert result is not None
    assert result.edit_type == "insertion"
    assert result.edit_position == 0
    assert result.matching_letters == 2


def test_insertion_extra_char_in_middle():
    """Query has extra character in the middle."""
    # "toobe" has extra 'o' → removes to "tobe" which doesn't match "to be" (has space)
    # Better test: "wo rd" has extra space removed
    result = _try_insertion_at("be x", "be x or", 0)
    assert result is not None
    assert result.edit_type == "insertion"
    assert result.edit_position in [2, 3]  # Extra char at position 2 or 3


def test_insertion_extra_char_at_end():
    """Query has extra character at the end."""
    result = _try_insertion_at("wordd", "the word is", 4)
    assert result is not None
    assert result.edit_type == "insertion"
    # Both position 3 and 4 are valid (both 'd's can be removed)
    assert result.edit_position in [3, 4]
    assert result.matching_letters == 4


def test_insertion_no_match():
    """Query with extra char still doesn't match."""
    result = _try_insertion_at("xyz", "to be or", 0)
    assert result is None


# Deletion tests

def test_deletion_missing_char_at_start():
    """Query is missing first character."""
    result = _try_deletion_at("o be", "to be or", 0)
    assert result is not None
    assert result.edit_type == "deletion"
    assert result.edit_position == 0  # Missing 't'
    assert result.matching_letters == 4


def test_deletion_missing_char_in_middle():
    """Query is missing middle character."""
    result = _try_deletion_at("wrd", "the word is", 4)
    assert result is not None
    assert result.edit_type == "deletion"
    # Position is in the window where the char exists, query is missing it
    assert result.edit_position in [1, 2]  # Could be 'o' position in window
    assert result.matching_letters == 3


def test_deletion_missing_char_at_end():
    """Query is missing last character."""
    result = _try_deletion_at("wor", "the word is", 4)
    assert result is not None
    assert result.edit_type == "deletion"
    assert result.edit_position == 3  # Missing 'd'


def test_deletion_no_match():
    """Query is missing char but still doesn't match."""
    result = _try_deletion_at("xyz", "to be or not", 0)
    assert result is None


# Integration tests with find_best_match_score

def test_find_best_match_exact():
    """Find exact match and return correct score."""
    score = find_best_match_score("be", "to be or not")
    assert score == 4  # 2×2 = 4, exact match at position 3


def test_find_best_match_multiple_positions():
    """When query appears multiple times, return best score."""
    score = find_best_match_score("be", "to be or not to be")
    assert score == 4  # Same score at both positions


def test_find_best_match_no_match():
    """Return None when no match found."""
    score = find_best_match_score("xyz", "to be or not")
    assert score is None


def test_find_best_match_query_longer_than_sentence():
    """Query longer than sentence should return None."""
    score = find_best_match_score("this is a very long query", "short")
    assert score is None


def test_find_best_match_prefers_better_score():
    """When multiple match types exist, return the best score."""
    # "to" exact match at pos 0: score = 4
    # "to" with edits at other positions will have lower scores
    score = find_best_match_score("to", "to be or not to be")
    assert score == 4  # Best is exact match


def test_find_best_match_keeps_zero_score_when_later_scores_are_lower():
    score = find_best_match_score("aa", "abcde")

    assert score == 0


def test_find_best_match_repeated_extra_query_character_regressions():
    assert find_best_match_score("wordd", "word") == 6
    assert find_best_match_score("woord", "word") == 2
    assert find_best_match_score("aaa", "aa") == -2


def test_find_best_match_repeated_and_zero_score_regressions():
    assert find_best_match_score("ab", "aa") == 0
    assert find_best_match_score("aab", "abcde") == -4


def test_pdf_example_sentence():
    """Test with actual PDF example sentence."""
    sentence = "to be or not to be that is the question"
    
    # Exact match
    score = find_best_match_score("to be", sentence)
    assert score == 10  # 2×5
    
    # Match at different positions should give same score
    score = find_best_match_score("or not", sentence)
    assert score == 12  # 2×6

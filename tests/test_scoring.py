"""Tests for the scoring module."""

from autocomplete.models import Match
from autocomplete.scoring import calculate_score


def test_exact_match_scoring():
    """Exact match should have no penalty."""
    match = Match(edit_type="exact", edit_position=None, matching_letters=5)
    assert calculate_score(match) == 10  # 2 × 5


def test_substitution_position_0():
    """Substitution at first position has -5 penalty."""
    match = Match(edit_type="substitution", edit_position=0, matching_letters=4)
    assert calculate_score(match) == 3  # 2×4 - 5


def test_substitution_position_1():
    """Substitution at second position has -4 penalty."""
    match = Match(edit_type="substitution", edit_position=1, matching_letters=4)
    assert calculate_score(match) == 4  # 2×4 - 4


def test_substitution_position_2():
    """Substitution at third position has -3 penalty."""
    match = Match(edit_type="substitution", edit_position=2, matching_letters=4)
    assert calculate_score(match) == 5  # 2×4 - 3


def test_substitution_position_3():
    """Substitution at fourth position has -2 penalty."""
    match = Match(edit_type="substitution", edit_position=3, matching_letters=4)
    assert calculate_score(match) == 6  # 2×4 - 2


def test_substitution_position_4_plus():
    """Substitution at position 4+ has -1 penalty."""
    match = Match(edit_type="substitution", edit_position=4, matching_letters=10)
    assert calculate_score(match) == 19  # 2×10 - 1
    
    match = Match(edit_type="substitution", edit_position=9, matching_letters=11)
    assert calculate_score(match) == 21  # 2×11 - 1


def test_insertion_position_0():
    """Insertion at first position has -10 penalty."""
    match = Match(edit_type="insertion", edit_position=0, matching_letters=5)
    assert calculate_score(match) == 0  # 2×5 - 10


def test_insertion_position_1():
    """Insertion at second position has -8 penalty."""
    match = Match(edit_type="insertion", edit_position=1, matching_letters=5)
    assert calculate_score(match) == 2  # 2×5 - 8


def test_insertion_position_2():
    """Insertion at third position has -6 penalty."""
    match = Match(edit_type="insertion", edit_position=2, matching_letters=5)
    assert calculate_score(match) == 4  # 2×5 - 6


def test_insertion_position_3():
    """Insertion at fourth position has -4 penalty."""
    match = Match(edit_type="insertion", edit_position=3, matching_letters=5)
    assert calculate_score(match) == 6  # 2×5 - 4


def test_insertion_position_4_plus():
    """Insertion at position 4+ has -2 penalty."""
    match = Match(edit_type="insertion", edit_position=4, matching_letters=5)
    assert calculate_score(match) == 8  # 2×5 - 2
    
    match = Match(edit_type="insertion", edit_position=10, matching_letters=15)
    assert calculate_score(match) == 28  # 2×15 - 2


def test_deletion_position_0():
    """Deletion at first position has -10 penalty."""
    match = Match(edit_type="deletion", edit_position=0, matching_letters=3)
    assert calculate_score(match) == -4  # 2×3 - 10


def test_deletion_position_1():
    """Deletion at second position has -8 penalty."""
    match = Match(edit_type="deletion", edit_position=1, matching_letters=5)
    assert calculate_score(match) == 2  # 2×5 - 8


def test_deletion_position_2():
    """Deletion at third position has -6 penalty."""
    match = Match(edit_type="deletion", edit_position=2, matching_letters=5)
    assert calculate_score(match) == 4  # 2×5 - 6


def test_deletion_position_3():
    """Deletion at fourth position has -4 penalty."""
    match = Match(edit_type="deletion", edit_position=3, matching_letters=10)
    assert calculate_score(match) == 16  # 2×10 - 4


def test_deletion_position_4_plus():
    """Deletion at position 4+ has -2 penalty."""
    match = Match(edit_type="deletion", edit_position=4, matching_letters=7)
    assert calculate_score(match) == 12  # 2×7 - 2


def test_pdf_example_exact():
    """Test from PDF: 'להיות או לא' (10 chars) exact match."""
    match = Match(edit_type="exact", edit_position=None, matching_letters=10)
    assert calculate_score(match) == 20  # 2×10


def test_pdf_example_substitution():
    """Test from PDF: 'להיות או לו' substitution at position 9."""
    match = Match(edit_type="substitution", edit_position=9, matching_letters=10)
    assert calculate_score(match) == 19  # 2×10 - 1


def test_pdf_example_deletion():
    """Test from PDF: 'להות או לא' deletion at position 2."""
    match = Match(edit_type="deletion", edit_position=2, matching_letters=10)
    assert calculate_score(match) == 14  # 2×10 - 6

import pytest

from autocomplete.models import SentenceRecord
from autocomplete.normalization import normalize_text

from typing import cast

def test_empty_string_returns_empty_string():
    assert normalize_text("") == ""


def test_lowercase_input_is_preserved():
    assert normalize_text("already lowercase") == "already lowercase"


def test_mixed_case_is_lowercased():
    assert normalize_text("MiXeD Case") == "mixed case"


def test_leading_trailing_and_repeated_whitespace_collapses():
    assert normalize_text(" \t  hello\n\n   world  ") == "hello world"


def test_common_punctuation_is_replaced_with_spaces():
    text = "Hello, world. \"Ready?\" Yes! well-known"

    assert normalize_text(text) == "hello world ready yes well known"


def test_adjacent_words_separated_by_punctuation_do_not_merge():
    assert normalize_text("word,word hello-world") == "word word hello world"


def test_punctuation_only_input_returns_empty_string():
    assert normalize_text("?!.,---\"\"") == ""


def test_numbers_are_preserved():
    assert normalize_text("Version 2.0 costs $5!") == "version 2 0 costs $5"


def test_original_text_can_remain_unchanged_in_record():
    original = "Hello, WORLD!"
    record = SentenceRecord(
        original_text=original,
        normalized_text=normalize_text(original),
        source_path=__file__,
        line_number=1,
    )

    assert record.original_text == "Hello, WORLD!"
    assert record.normalized_text == "hello world"


def test_unicode_text_is_supported():
    assert normalize_text("Café-au-lait שלום!") == "café au lait שלום"


def test_unicode_case_uses_lower_not_casefold():
    assert normalize_text("Straße") == "straße"


def test_non_string_values_raise_type_error():
    invalid_text = cast(str, None)

    with pytest.raises(TypeError, match="expects a str"):
        normalize_text(invalid_text)

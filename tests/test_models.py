from dataclasses import is_dataclass
from typing import get_type_hints

from autocomplete.models import AutoCompleteData, SentenceRecord


def test_sentence_record_model_contract():
    record = SentenceRecord(
        original_text="Example",
        normalized_text="example",
        source_path="source.txt",
        line_number=1,
    )

    assert is_dataclass(record)
    assert list(vars(record)) == [
        "original_text",
        "normalized_text",
        "source_path",
        "line_number",
    ]
    assert list(get_type_hints(SentenceRecord).values()) == [
        str,
        str,
        str,
        int,
    ]


def test_auto_complete_data_model_contract():
    result = AutoCompleteData(
        completed_sentence="Example",
        source_text="source.txt",
        offset=1,
        score=10,
    )

    assert is_dataclass(result)
    assert list(vars(result)) == [
        "completed_sentence",
        "source_text",
        "offset",
        "score",
    ]
    assert list(get_type_hints(AutoCompleteData).values()) == [
        str,
        str,
        int,
        int,
    ]


def test_auto_complete_data_offset_uses_one_based_line_number_meaning():
    result = AutoCompleteData(
        completed_sentence="Hello world",
        source_text="source.txt",
        offset=3,
        score=10,
    )

    assert result.offset == 3
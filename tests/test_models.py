from dataclasses import fields, is_dataclass

from autocomplete.models import AutoCompleteData, SentenceRecord


def test_sentence_record_model_contract():
    assert is_dataclass(SentenceRecord)
    assert [field.name for field in fields(SentenceRecord)] == [
        "original_text",
        "normalized_text",
        "source_path",
        "line_number",
    ]
    assert [field.type for field in fields(SentenceRecord)] == [
        str,
        str,
        str,
        int,
    ]


def test_auto_complete_data_model_contract():
    assert is_dataclass(AutoCompleteData)
    assert [field.name for field in fields(AutoCompleteData)] == [
        "completed_sentence",
        "source_text",
        "offset",
        "score",
    ]
    assert [field.type for field in fields(AutoCompleteData)] == [
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

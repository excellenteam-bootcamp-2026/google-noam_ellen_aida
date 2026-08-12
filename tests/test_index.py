import json
from pathlib import Path
from typing import cast

import pytest

from autocomplete.index import build_index, load_index, save_index
from autocomplete.loader import load_sentence_records
from autocomplete.models import PreparedSentenceIndex, SentenceRecord
from autocomplete.service import search_records
from reference_oracle import linear_autocomplete


def test_build_index_from_fixture_directory():
    fixture_dir = Path(__file__).parent / "fixtures" / "sample_sentences"

    data = build_index(load_sentence_records(fixture_dir))

    assert isinstance(data, PreparedSentenceIndex)
    assert len(data.records) == 4
    assert data.records[0].original_text == "Hello, World!"
    assert data.records[0].normalized_text == "hello world"


def test_save_load_round_trip_preserves_record_fields(tmp_path):
    source_path = tmp_path / "unicode.txt"
    record = SentenceRecord(
        original_text="Café-au-lait?",
        normalized_text="café au lait",
        source_path=str(source_path),
        line_number=3,
    )
    data = build_index([record])
    index_path = tmp_path / "prepared" / "index.json"

    save_index(data, index_path)
    loaded = load_index(index_path)

    assert loaded == data


def test_multiple_record_round_trip_preserves_order(tmp_path):
    records = [
        SentenceRecord("First", "first", "a.txt", 1),
        SentenceRecord("Second", "second", "b.txt", 7),
    ]
    index_path = tmp_path / "index.json"

    save_index(build_index(records), str(index_path))

    assert load_index(str(index_path)).records == tuple(records)


def test_empty_index_round_trip(tmp_path):
    index_path = tmp_path / "index.json"
    data = build_index([])

    save_index(data, index_path)

    assert load_index(index_path) == data


def test_build_index_rejects_non_record():
    invalid_record = cast(SentenceRecord, object())

    with pytest.raises(TypeError, match="SentenceRecord"):
        build_index([invalid_record])


def test_missing_index_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_index(tmp_path / "missing.json")


def test_invalid_json_raises_value_error(tmp_path):
    index_path = tmp_path / "broken.json"
    index_path.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid index JSON"):
        load_index(index_path)


def test_malformed_index_missing_record_field_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 1,
                "records": [
                    {
                        "original_text": "Hello",
                        "normalized_text": "hello",
                        "source_path": "source.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="line_number"):
        load_index(index_path)


def test_malformed_index_boolean_line_number_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 1,
                "records": [
                    {
                        "line_number": True,
                        "original_text": "Hello",
                        "normalized_text": "hello",
                        "source_path": "source.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="positive integer"):
        load_index(index_path)


def test_malformed_index_wrong_top_level_type_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        load_index(index_path)


def test_malformed_index_extra_top_level_field_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 1,
                "records": [],
                "extra": "unexpected",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unexpected field"):
        load_index(index_path)


def test_malformed_index_extra_record_field_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 1,
                "records": [
                    {
                        "line_number": 1,
                        "original_text": "Hello",
                        "normalized_text": "hello",
                        "source_path": "source.txt",
                        "extra": "unexpected",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unexpected field"):
        load_index(index_path)


def test_malformed_index_wrong_field_type_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 1,
                "records": [
                    {
                        "line_number": 1,
                        "original_text": ["Hello"],
                        "normalized_text": "hello",
                        "source_path": "source.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="original_text"):
        load_index(index_path)


def test_malformed_index_invalid_line_number_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 1,
                "records": [
                    {
                        "line_number": 0,
                        "original_text": "Hello",
                        "normalized_text": "hello",
                        "source_path": "source.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="positive integer"):
        load_index(index_path)


def test_malformed_index_boolean_version_raises_value_error(tmp_path):
    index_path = tmp_path / "malformed.json"
    index_path.write_text(
        json.dumps({"format": "autocomplete-index", "version": True, "records": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported index version"):
        load_index(index_path)


def test_unsupported_index_format_raises_value_error(tmp_path):
    index_path = tmp_path / "unsupported.json"
    index_path.write_text(
        json.dumps({"format": "other", "version": 1, "records": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported index format"):
        load_index(index_path)


def test_deterministic_serialized_output(tmp_path):
    record = SentenceRecord(
        original_text="Hello",
        normalized_text="hello",
        source_path="source.txt",
        line_number=1,
    )
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    data = build_index([record])
    save_index(data, first)
    save_index(data, second)

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    assert "Hello" in first.read_text(encoding="utf-8")


def test_save_load_search_equivalence_matches_oracle(tmp_path):
    records = [
        SentenceRecord("word", "word", "a.txt", 1),
        SentenceRecord("word", "word", "a.txt", 2),
        SentenceRecord("word", "word", "b.txt", 1),
        SentenceRecord("alpha one", "alpha one", "c.txt", 1),
        SentenceRecord("alpha two", "alpha two", "c.txt", 2),
        SentenceRecord("alpha three", "alpha three", "c.txt", 3),
        SentenceRecord("alpha four", "alpha four", "c.txt", 4),
        SentenceRecord("alpha five", "alpha five", "c.txt", 5),
        SentenceRecord("alpha six", "alpha six", "c.txt", 6),
    ]
    queries = ("word", "wprd", "wrd", "wordd", "alpha", "missing")
    index_path = tmp_path / "index.json"

    before = {query: search_records(query, records) for query in queries}
    save_index(build_index(records), index_path)
    loaded_records = list(load_index(index_path).records)
    after = {query: search_records(query, loaded_records) for query in queries}
    oracle = {query: linear_autocomplete(query, records) for query in queries}

    assert after == before
    assert after == oracle


def test_empty_index_search_equivalence(tmp_path):
    index_path = tmp_path / "empty.json"
    save_index(build_index([]), index_path)

    loaded_records = list(load_index(index_path).records)

    assert search_records("alpha", loaded_records) == []
    assert search_records("alpha", loaded_records) == linear_autocomplete("alpha", [])

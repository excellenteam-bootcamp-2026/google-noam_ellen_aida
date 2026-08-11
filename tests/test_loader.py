from pathlib import Path

import pytest

from autocomplete.loader import iter_text_files, load_sentence_records


def test_loads_one_text_file(tmp_path):
    source = tmp_path / "sentences.txt"
    source.write_text("Hello, World!\n", encoding="utf-8")

    records = load_sentence_records(source)

    assert len(records) == 1
    assert records[0].original_text == "Hello, World!"
    assert records[0].normalized_text == "hello world"
    assert records[0].source_path == str(source)
    assert records[0].line_number == 1


def test_loads_from_string_path(tmp_path):
    source = tmp_path / "sentences.txt"
    source.write_text("Hello\n", encoding="utf-8")

    records = load_sentence_records(str(source))

    assert [record.original_text for record in records] == ["Hello"]


def test_loads_multiple_text_files_in_sorted_order(tmp_path):
    b_file = tmp_path / "b.txt"
    a_file = tmp_path / "a.txt"
    b_file.write_text("B line\n", encoding="utf-8")
    a_file.write_text("A line\n", encoding="utf-8")

    records = load_sentence_records(tmp_path)

    assert [record.source_path for record in records] == [str(a_file), str(b_file)]
    assert [record.original_text for record in records] == ["A line", "B line"]


def test_loads_nested_directories_and_ignores_non_txt(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    root_txt = tmp_path / "root.txt"
    nested_txt = nested / "child.txt"
    ignored = nested / "child.md"
    root_txt.write_text("Root\n", encoding="utf-8")
    nested_txt.write_text("Child\n", encoding="utf-8")
    ignored.write_text("Ignored\n", encoding="utf-8")

    records = load_sentence_records(tmp_path)

    assert [record.source_path for record in records] == [str(nested_txt), str(root_txt)]
    assert [record.original_text for record in records] == ["Child", "Root"]


def test_empty_file_and_empty_directory_return_no_records(tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    assert load_sentence_records(empty_file) == []
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert load_sentence_records(empty_dir) == []


def test_blank_lines_are_skipped_but_count_for_line_numbers(tmp_path):
    source = tmp_path / "sentences.txt"
    source.write_text("First record\n\nSecond record\n", encoding="utf-8")

    records = load_sentence_records(source)

    assert [record.original_text for record in records] == [
        "First record",
        "Second record",
    ]
    assert [record.line_number for record in records] == [1, 3]


def test_whitespace_and_punctuation_only_lines_are_skipped_but_counted(tmp_path):
    source = tmp_path / "sentences.txt"
    source.write_text("First\n   \n!!!\nSecond\n", encoding="utf-8")

    records = load_sentence_records(source)

    assert [record.original_text for record in records] == ["First", "Second"]
    assert [record.line_number for record in records] == [1, 4]


def test_source_path_and_line_endings_are_preserved(tmp_path):
    source = tmp_path / "sentences.txt"
    source.write_text("Keep punctuation!\r\nTrailing spaces   \n", encoding="utf-8")

    records = load_sentence_records(source)

    assert records[0].original_text == "Keep punctuation!"
    assert records[0].source_path == str(source)
    assert records[1].original_text == "Trailing spaces   "


def test_missing_path_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_sentence_records(tmp_path / "missing")


def test_utf8_content_is_loaded(tmp_path):
    source = tmp_path / "unicode.txt"
    source.write_text("Café שלום\n", encoding="utf-8")

    records = load_sentence_records(source)

    assert records[0].original_text == "Café שלום"
    assert records[0].normalized_text == "café שלום"


def test_invalid_utf8_raises_unicode_decode_error(tmp_path):
    source = tmp_path / "broken.txt"
    source.write_bytes(b"valid\n\xff\n")

    with pytest.raises(UnicodeDecodeError):
        load_sentence_records(source)


def test_non_txt_file_argument_is_ignored(tmp_path):
    source = tmp_path / "notes.md"
    source.write_text("Ignored\n", encoding="utf-8")

    assert list(iter_text_files(source)) == []
    assert load_sentence_records(source) == []


def test_fixture_directory_is_recursive():
    fixture_dir = Path(__file__).parent / "fixtures" / "sample_sentences"

    records = load_sentence_records(fixture_dir)

    assert [record.original_text for record in records] == [
        "Hello, World!",
        "Second line.",
        "Café-au-lait?",
        "Numbers 123 stay.",
    ]


def test_repeated_calls_produce_same_ordering(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "b.txt").write_text("B\n", encoding="utf-8")
    (nested / "a.txt").write_text("A\n", encoding="utf-8")

    first = load_sentence_records(tmp_path)
    second = load_sentence_records(tmp_path)

    assert first == second

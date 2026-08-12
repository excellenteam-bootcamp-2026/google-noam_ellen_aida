from pathlib import Path

from autocomplete import service
from autocomplete.loader import load_sentence_records
from autocomplete.models import AutoCompleteData, SentenceRecord
from autocomplete.normalization import normalize_text

from reference_oracle import (
    find_best_linear_match_score,
    linear_autocomplete,
    score_window,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "reference_oracle"


def make_record(text: str, source: str = "source.txt", line_number: int = 1) -> SentenceRecord:
    return SentenceRecord(
        original_text=text,
        normalized_text=normalize_text(text),
        source_path=source,
        line_number=line_number,
    )


def test_linear_oracle_exact_matches_beginning_middle_and_end() -> None:
    assert find_best_linear_match_score("alpha", "alpha begins here") == 10
    assert find_best_linear_match_score("alpha", "middle alpha token") == 10
    assert find_best_linear_match_score("omega", "ends with omega") == 10


def test_linear_oracle_replacement_penalty_positions() -> None:
    assert find_best_linear_match_score("xbcde", "abcde") == 5
    assert find_best_linear_match_score("axcde", "abcde") == 6
    assert find_best_linear_match_score("abxde", "abcde") == 7
    assert find_best_linear_match_score("abcxe", "abcde") == 8
    assert find_best_linear_match_score("abcdx", "abcde") == 9


def test_linear_oracle_missing_query_character_penalty_positions() -> None:
    assert list(score_window("bcde", "abcde"))[-1].score == -2
    assert list(score_window("acde", "abcde"))[-1].score == 0
    assert list(score_window("abde", "abcde"))[-1].score == 2
    assert list(score_window("abce", "abcde"))[-1].score == 4
    assert list(score_window("abcd", "abcde"))[-1].score == 6


def test_linear_oracle_extra_query_character_penalty_positions() -> None:
    assert list(score_window("xabcde", "abcde"))[-1].score == 0
    assert list(score_window("axbcde", "abcde"))[-1].score == 2
    assert list(score_window("abxcde", "abcde"))[-1].score == 4
    assert list(score_window("abcxde", "abcde"))[-1].score == 6
    assert list(score_window("abcdxe", "abcde"))[-1].score == 8


def test_linear_oracle_rejects_two_edits_and_too_long_query() -> None:
    assert find_best_linear_match_score("axcxe", "abcde") is None
    assert find_best_linear_match_score("much longer query", "short") is None


def test_linear_oracle_handles_query_lengths_one_through_five_plus() -> None:
    sentence = "abcdefg"

    assert find_best_linear_match_score("a", sentence) == 2
    assert find_best_linear_match_score("ab", sentence) == 4
    assert find_best_linear_match_score("abc", sentence) == 6
    assert find_best_linear_match_score("abcd", sentence) == 8
    assert find_best_linear_match_score("abcdef", sentence) == 12


def test_linear_oracle_empty_whitespace_and_punctuation_queries_return_no_results() -> None:
    records = [make_record("hello world")]

    assert linear_autocomplete("", records) == []
    assert linear_autocomplete("   \t", records) == []
    assert linear_autocomplete("?!.,---", records) == []


def test_linear_oracle_uses_shared_normalization_for_case_punctuation_spaces() -> None:
    records = [
        make_record("Punctuated hello-world", "a.txt", 1),
        make_record("spaced words match", "b.txt", 2),
    ]

    assert linear_autocomplete("HELLO WORLD", records) == [
        AutoCompleteData("Punctuated hello-world", "a.txt", 1, 22)
    ]
    assert linear_autocomplete("words   match", records) == [
        AutoCompleteData("spaced words match", "b.txt", 2, 22)
    ]


def test_linear_oracle_preserves_duplicate_occurrences_and_metadata() -> None:
    records = [
        make_record("Same duplicate", "a.txt", 1),
        make_record("Same duplicate", "a.txt", 2),
        make_record("Same duplicate", "nested/b.txt", 1),
    ]

    assert linear_autocomplete("duplicate", records) == [
        AutoCompleteData("Same duplicate", "a.txt", 1, 18),
        AutoCompleteData("Same duplicate", "a.txt", 2, 18),
        AutoCompleteData("Same duplicate", "nested/b.txt", 1, 18),
    ]


def test_linear_oracle_ranks_score_sentence_source_offset_and_limits_to_five() -> None:
    records = [
        make_record("Zulu alpha", "z.txt", 9),
        make_record("alpha one", "b.txt", 2),
        make_record("Alpha one", "a.txt", 1),
        make_record("alpha two", "a.txt", 3),
        make_record("alpha three", "a.txt", 4),
        make_record("alpha four", "a.txt", 5),
        make_record("alpha five", "a.txt", 6),
    ]

    assert linear_autocomplete("alpha", records) == [
        AutoCompleteData("alpha five", "a.txt", 6, 10),
        AutoCompleteData("alpha four", "a.txt", 5, 10),
        AutoCompleteData("Alpha one", "a.txt", 1, 10),
        AutoCompleteData("alpha one", "b.txt", 2, 10),
        AutoCompleteData("alpha three", "a.txt", 4, 10),
    ]


def test_linear_oracle_retains_highest_scoring_alignment_per_record() -> None:
    records = [make_record("abcde abcxe", "a.txt", 1)]

    assert linear_autocomplete("abcxe", records) == [
        AutoCompleteData("abcde abcxe", "a.txt", 1, 10)
    ]


def test_linear_oracle_chooses_best_repeated_character_interpretation() -> None:
    alignments = list(score_window("wordd", "word"))

    assert [alignment.score for alignment in alignments] == [4, 6]
    assert find_best_linear_match_score("wordd", "word") == 6


def test_linear_oracle_fixture_loads_nested_files_without_full_corpus() -> None:
    records = load_sentence_records(FIXTURE_DIR)

    assert [record.original_text for record in records][:3] == [
        "Same duplicate",
        "Another alpha line",
        "alpha three",
    ]
    assert len(linear_autocomplete("alpha", records)) == 5


def test_current_service_matches_oracle_for_representative_queries(monkeypatch) -> None:
    records = load_sentence_records(FIXTURE_DIR)
    monkeypatch.setattr(service, "_records", records)

    for query in [
        "alpha",
        "HELLO WORLD",
        "omega",
        "wprd",
        "wrd",
        "wordx",
        "no-such-query",
        "",
        "?!",
    ]:
        assert service.get_best_k_completions(query) == linear_autocomplete(query, records)


def test_current_service_matches_oracle_for_repeated_extra_character(monkeypatch) -> None:
    records = [make_record("word", "a.txt", 1)]
    monkeypatch.setattr(service, "_records", records)

    expected = linear_autocomplete("wordd", records)
    actual = service.get_best_k_completions("wordd")

    assert expected == [AutoCompleteData("word", "a.txt", 1, 6)]
    assert actual == expected


def test_linear_oracle_stable_across_repeated_runs() -> None:
    records = load_sentence_records(FIXTURE_DIR)

    first = linear_autocomplete("alpha", records)
    second = linear_autocomplete("alpha", records)

    assert first == second

from autocomplete.comparison import ComparisonRunner, compare_result_lists
from autocomplete.models import AutoCompleteData, SentenceRecord


def result(
    sentence: str = "Alpha",
    source: str = "a.txt",
    offset: int = 1,
    score: int = 10,
) -> AutoCompleteData:
    return AutoCompleteData(sentence, source, offset, score)


def test_compare_result_lists_accepts_identical_outputs() -> None:
    comparison = compare_result_lists("alpha", [result()], [result()])

    assert comparison.passed
    assert comparison.mismatches == ()


def test_compare_result_lists_detects_different_sentence() -> None:
    comparison = compare_result_lists("alpha", [result("Alpha")], [result("Beta")])

    assert not comparison.passed
    assert comparison.mismatches[0].category == "missing_result"
    assert comparison.mismatches[0].differing_fields == ("completed_sentence",)


def test_compare_result_lists_detects_different_score() -> None:
    comparison = compare_result_lists("alpha", [result(score=10)], [result(score=8)])

    assert not comparison.passed
    assert comparison.mismatches[0].category == "score_mismatch"
    assert comparison.mismatches[0].differing_fields == ("score",)


def test_compare_result_lists_detects_different_path() -> None:
    comparison = compare_result_lists("alpha", [result(source="a.txt")], [result(source="b.txt")])

    assert not comparison.passed
    assert comparison.mismatches[0].category == "metadata_mismatch"
    assert comparison.mismatches[0].differing_fields == ("source_text",)


def test_compare_result_lists_detects_different_offset() -> None:
    comparison = compare_result_lists("alpha", [result(offset=1)], [result(offset=2)])

    assert not comparison.passed
    assert comparison.mismatches[0].category == "metadata_mismatch"
    assert comparison.mismatches[0].differing_fields == ("offset",)


def test_compare_result_lists_detects_different_result_count() -> None:
    comparison = compare_result_lists(
        "alpha",
        [result("Alpha"), result("Beta")],
        [result("Alpha")],
    )

    assert not comparison.passed
    assert comparison.mismatches[0].category == "count_mismatch"
    assert comparison.mismatches[0].differing_fields == ("result_count",)


def test_compare_result_lists_detects_ordering_mismatch() -> None:
    oracle = [result("Alpha"), result("Beta")]
    production = [result("Beta"), result("Alpha")]

    comparison = compare_result_lists("alpha", oracle, production)

    assert not comparison.passed
    assert comparison.mismatches[0].category == "ordering_mismatch"


def test_compare_result_lists_preserves_duplicate_occurrences() -> None:
    oracle = [result("Alpha", offset=1), result("Alpha", offset=2)]
    production = [result("Alpha", offset=1), result("Alpha", offset=1)]

    comparison = compare_result_lists("alpha", oracle, production)

    assert not comparison.passed
    assert comparison.mismatches[0].category == "metadata_mismatch"


def test_compare_result_lists_detects_top_five_mismatch() -> None:
    oracle = [result(f"Sentence {index}") for index in range(5)]
    production = [*oracle[:4], result("Unexpected")]

    comparison = compare_result_lists("alpha", oracle, production)

    assert not comparison.passed
    assert comparison.mismatches[0].category == "top_five_mismatch"


def test_compare_result_lists_detects_missing_and_unexpected_results() -> None:
    missing = compare_result_lists("alpha", [result()], [])
    unexpected = compare_result_lists("alpha", [], [result()])

    assert missing.mismatches[0].category == "missing_result"
    assert unexpected.mismatches[0].category == "unexpected_result"


def test_comparison_runner_reports_summary_and_exit_code() -> None:
    records = [SentenceRecord("Alpha", "alpha", "a.txt", 1)]

    def oracle_search(_query, _records):
        return [result()]

    def production_search(_query, _records):
        return [result(score=8)]

    summary = ComparisonRunner(
        records=records,
        queries=("alpha",),
        oracle_search=oracle_search,
        production_search=production_search,
    ).run()

    assert summary.total_queries == 1
    assert summary.passed_queries == 0
    assert summary.failed_queries == 1
    assert summary.agreement_percentage == 0.0
    assert summary.mismatch_counts == {"score_mismatch": 1}
    assert summary.exit_code == 1


def test_comparison_runner_reports_unexpected_exceptions() -> None:
    records = [SentenceRecord("Alpha", "alpha", "a.txt", 1)]

    def oracle_search(_query, _records):
        return [result()]

    def broken_search(_query, _records):
        raise RuntimeError("broken")

    summary = ComparisonRunner(
        records=records,
        queries=("alpha",),
        oracle_search=oracle_search,
        production_search=broken_search,
    ).run()

    assert summary.failed_queries == 1
    assert summary.exceptions[0].category == "exception"
    assert summary.exit_code == 1

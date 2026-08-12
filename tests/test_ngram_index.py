import json
from itertools import product
from pathlib import Path
from random import Random

import pytest

from autocomplete.index import build_index, load_index, save_index
from autocomplete.models import SentenceRecord
from autocomplete.ngram import (
    build_ngram_index,
    candidate_record_ids,
    measure_candidate_recall,
    uses_full_scan,
)
from autocomplete.normalization import normalize_text
from autocomplete.service import search_index, search_records
from reference_oracle import linear_autocomplete


def make_record(
    text: str,
    source: str = "source.txt",
    line_number: int = 1,
) -> SentenceRecord:
    return SentenceRecord(
        original_text=text,
        normalized_text=normalize_text(text),
        source_path=source,
        line_number=line_number,
    )


def canonical_matching_ids(query: str, records: list[SentenceRecord]) -> set[int]:
    normalized_query = normalize_text(query)
    return {
        record_id
        for record_id, record in enumerate(records)
        if search_records(query, [record])
        and normalized_query
    }


def assert_optimized_equals_canonical(
    query: str,
    records: list[SentenceRecord],
) -> None:
    prepared = build_index(records)

    assert search_index(query, prepared) == search_records(query, records)
    assert search_index(query, prepared) == linear_autocomplete(query, records)


def assert_recall_safe(query: str, records: list[SentenceRecord]) -> None:
    prepared = build_index(records)
    normalized_query = normalize_text(query)
    candidates = set(
        candidate_record_ids(normalized_query, prepared.records, prepared.ngram_index)
    )
    matching = canonical_matching_ids(query, records)

    assert matching.issubset(candidates)
    diagnostics = measure_candidate_recall(
        query,
        prepared.records,
        prepared.ngram_index,
        final_result_count=len(search_index(query, prepared)),
    )
    assert diagnostics.false_negatives == 0
    if diagnostics.canonical_matching_records:
        assert diagnostics.candidate_recall == 1.0


def test_ngram_index_assigns_stable_record_ids_and_deduplicates_postings() -> None:
    records = [
        make_record("banana", "a.txt", 1),
        make_record("banana", "a.txt", 2),
        make_record("bandana", "b.txt", 1),
        make_record("Café-au-lait?", "c.txt", 1),
    ]

    index = build_ngram_index(records)

    assert list(index.postings[2]["ba"]) == [0, 1, 2]
    assert list(index.postings[3]["ban"]) == [0, 1, 2]
    assert list(index.postings[3]["ana"]) == [0, 1, 2]
    assert list(index.postings[3]["afé"]) == [3]
    assert len(index.postings[2]["an"]) == len(set(index.postings[2]["an"]))


def test_ngram_candidate_generation_is_recall_safe_for_required_categories() -> None:
    records = [
        make_record("abcde", "a.txt", 1),
        make_record("xx abcde yy", "a.txt", 2),
        make_record("word", "b.txt", 1),
        make_record("word word", "b.txt", 2),
        make_record("alpha one", "c.txt", 1),
        make_record("alpha two", "c.txt", 2),
        make_record("alpha three", "c.txt", 3),
        make_record("Punctuated hello-world", "d.txt", 1),
        make_record("spaced words match", "e.txt", 1),
    ]
    queries = [
        "abcde",
        "xbcde",
        "abxde",
        "abcdx",
        "bcde",
        "abde",
        "abcd",
        "xabcde",
        "abxcde",
        "abcdex",
        "wordd",
        "woord",
        "HELLO WORLD",
        "words   match",
        "alpha",
        "no-such-query",
        "",
        "?!",
        "a",
        "ab",
        "abc",
        "abcdefghi",
        "this is a query longer than twenty",
    ]

    for query in queries:
        assert_recall_safe(query, records)
        assert_optimized_equals_canonical(query, records)


def test_short_queries_use_full_scan_fallback() -> None:
    prepared = build_index([make_record("abc"), make_record("xyz")])

    assert not uses_full_scan("", prepared.ngram_index)
    assert uses_full_scan("a", prepared.ngram_index)
    assert uses_full_scan("ab", prepared.ngram_index)
    assert uses_full_scan("abc", prepared.ngram_index)
    assert not uses_full_scan("abcd", prepared.ngram_index)


def test_naive_all_gram_intersection_false_negative_case_is_preserved() -> None:
    records = [make_record("abcde")]
    prepared = build_index(records)

    candidates = candidate_record_ids("abxde", prepared.records, prepared.ngram_index)

    assert set(candidates) == {0}
    assert search_index("abxde", prepared) == search_records("abxde", records)


def test_exhaustive_small_alphabet_matches_canonical() -> None:
    alphabet = "ab "
    records = [
        make_record("".join(chars), "exhaustive.txt", index + 1)
        for index, chars in enumerate(product(alphabet, repeat=4))
    ]
    queries = {
        "".join(chars)
        for length in range(1, 6)
        for chars in product(alphabet, repeat=length)
    }

    for query in sorted(queries):
        assert_optimized_equals_canonical(query, records)
        assert_recall_safe(query, records)


def test_deterministic_randomized_queries_match_canonical() -> None:
    random = Random(20260812)
    alphabet = "abc "
    records = [
        make_record(
            "".join(random.choice(alphabet) for _ in range(random.randint(4, 12))),
            "random.txt",
            index + 1,
        )
        for index in range(80)
    ]
    queries = ["", "?!", "a", "ab", "abc", "aaaa", "abab", "no-match-query"]
    for record in records[:20]:
        text = record.normalized_text
        if len(text) >= 5:
            start = random.randrange(0, len(text) - 3)
            exact = text[start : start + 4]
            queries.append(exact)
            queries.append("x" + exact)
            queries.append(exact[:-1])
            queries.append(exact[:2] + "x" + exact[2:])

    for query in queries:
        assert_optimized_equals_canonical(query, records)
        assert_recall_safe(query, records)


def test_ngram_index_persists_and_legacy_indexes_rebuild_postings(
    tmp_path: Path,
) -> None:
    records = [make_record("alpha beta", "a.txt", 1), make_record("gamma", "b.txt", 2)]
    prepared = build_index(records)
    index_path = tmp_path / "index.json"

    save_index(prepared, index_path)
    loaded = load_index(index_path)

    assert loaded == prepared
    assert search_index("alpha", loaded) == search_records("alpha", records)

    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 1,
                "records": [
                    {
                        "line_number": record.line_number,
                        "normalized_text": record.normalized_text,
                        "original_text": record.original_text,
                        "source_path": record.source_path,
                    }
                    for record in records
                ],
            }
        ),
        encoding="utf-8",
    )
    legacy = load_index(legacy_path)

    assert legacy.ngram_index is not None
    assert search_index("alpha", legacy) == search_records("alpha", records)


def test_ngram_persistence_rejects_malformed_postings(tmp_path: Path) -> None:
    index_path = tmp_path / "bad.json"
    index_path.write_text(
        json.dumps(
            {
                "format": "autocomplete-index",
                "version": 2,
                "records": [
                    {
                        "line_number": 1,
                        "normalized_text": "alpha",
                        "original_text": "alpha",
                        "source_path": "a.txt",
                    }
                ],
                "ngram_index": {
                    "min_query_length": 4,
                    "ngram_sizes": [2],
                    "postings": {"2": {"al": [0, 0]}},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="sorted and unique"):
        load_index(index_path)

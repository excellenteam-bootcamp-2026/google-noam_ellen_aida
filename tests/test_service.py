from pathlib import Path

import pytest

from autocomplete import service
from autocomplete.models import AutoCompleteData, SentenceRecord


@pytest.fixture(autouse=True)
def reset_service_state(monkeypatch) -> None:
    monkeypatch.setattr(service, "_records", None)


def make_record(text: str, source: str, line_number: int) -> SentenceRecord:
    return SentenceRecord(text, text.casefold(), source, line_number)


def test_initialize_loads_prepared_records(monkeypatch, tmp_path: Path) -> None:
    index_path = tmp_path / "sentences.index"
    index_path.touch()
    records = [make_record("Alpha", "a.txt", 0)]
    monkeypatch.setattr(service, "_load_index", lambda path: records)

    service.initialize(index_path)

    assert service._records == records


def test_initialize_rejects_missing_index(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Prepared index not found"):
        service.initialize(tmp_path / "missing.index")


def test_search_requires_initialization(monkeypatch) -> None:
    with pytest.raises(RuntimeError, match="has not been initialized"):
        service.get_best_k_completions("query")


def test_empty_normalized_query_returns_no_results(monkeypatch) -> None:
    monkeypatch.setattr(service, "_records", [])
    monkeypatch.setattr(service, "_normalize", lambda text: "")

    assert service.get_best_k_completions("!!!") == []


def test_results_are_ranked_and_limited_to_five(monkeypatch) -> None:
    records = [
        make_record("Zulu", "z.txt", 5),
        make_record("alpha", "b.txt", 4),
        make_record("Alpha", "a.txt", 3),
        make_record("Bravo", "b.txt", 2),
        make_record("Charlie", "c.txt", 1),
        make_record("Delta", "d.txt", 0),
    ]
    scores = {
        "zulu": 20,
        "alpha": 20,
        "bravo": 18,
        "charlie": 16,
        "delta": 14,
    }
    monkeypatch.setattr(service, "_records", records)
    monkeypatch.setattr(service, "_normalize", str.casefold)
    monkeypatch.setattr(
        service,
        "_find_best_match_score",
        lambda prefix, sentence: scores.get(sentence),
    )

    results = service.get_best_k_completions("A")

    assert results == [
        AutoCompleteData("Alpha", "a.txt", 3, 20),
        AutoCompleteData("alpha", "b.txt", 4, 20),
        AutoCompleteData("Zulu", "z.txt", 5, 20),
        AutoCompleteData("Bravo", "b.txt", 2, 18),
        AutoCompleteData("Charlie", "c.txt", 1, 16),
    ]


def test_nonmatching_records_are_omitted(monkeypatch) -> None:
    monkeypatch.setattr(
        service,
        "_records",
        [make_record("No match", "source.txt", 0)],
    )
    monkeypatch.setattr(service, "_normalize", str.casefold)
    monkeypatch.setattr(
        service,
        "_find_best_match_score",
        lambda prefix, sentence: None,
    )

    assert service.get_best_k_completions("query") == []

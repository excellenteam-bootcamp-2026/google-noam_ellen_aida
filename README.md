# Autocomplete Project

Phase A implements the data pipeline for a Google-style sentence autocomplete system in Python. It covers text normalization, recursive corpus loading, and saving/loading a prepared sentence index. Matching, typo correction, scoring, ranking, service behavior, and CLI behavior are later teammate-owned phases and are not complete here.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install development dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

Run tests:

```bash
python3 -m pytest
```

## Data Directories

Place the supplied raw corpus under `data/raw/` on each developer machine. Prepared indexes and caches belong under `data/prepared/`.

Raw corpus files and generated prepared data are intentionally ignored by Git and must not be committed. The `.gitkeep` files keep the empty directories in the repository.

## Person 1 Data Pipeline

The Phase A pipeline is:

```text
raw text files
-> recursive loader
-> original and normalized SentenceRecord objects
-> prepared index
-> future matching/service modules
```

Public modules:

- `autocomplete.normalization.normalize_text(text: str) -> str`
- `autocomplete.loader.iter_sentence_records(path: str | PathLike[str]) -> Iterator[SentenceRecord]`
- `autocomplete.loader.load_sentence_records(path: str | PathLike[str]) -> list[SentenceRecord]`
- `autocomplete.index.build_index(records: Iterable[SentenceRecord]) -> PreparedSentenceIndex`
- `autocomplete.index.save_index(data: PreparedSentenceIndex, path: str | PathLike[str]) -> None`
- `autocomplete.index.load_index(path: str | PathLike[str]) -> PreparedSentenceIndex`

Each `SentenceRecord` stores `original_text` unchanged except for removed line-ending characters, `normalized_text`, `source_path` as a string, and a one-based `line_number`. The first physical line in each source file is line 1. Blank, whitespace-only, and punctuation-only lines still count toward physical line numbers even though they are skipped as records.

`AutoCompleteData` is reserved for later autocomplete results with `completed_sentence`, `source_text`, `offset`, and `score`. When later modules create results from a `SentenceRecord`, `source_text` should contain the source file path and `offset` should use the record's one-based `line_number`.

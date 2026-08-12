# Autocomplete Project

Python implementation of the Google-style sentence autocomplete assignment.

The current project supports recursive corpus loading, text normalization,
prepared JSON index persistence, linear matching with one-character correction,
position-sensitive scoring, service-level ranking, and an interactive CLI that
uses a prepared index.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e ".[dev]"
```

In this repository, use the virtual-environment Python for checks:

```bash
.venv/bin/python -m pytest -q
```

## Data Directories

Place the supplied raw corpus under `data/raw/` on each developer machine.
Prepared indexes and caches belong under `data/prepared/`.

Raw corpus files and generated prepared data are ignored by Git and must not be
committed. The `.gitkeep` files keep the empty directories in the repository.

## Current Pipeline

```text
raw text files
-> recursive loader
-> original and normalized SentenceRecord objects
-> prepared JSON index
-> service loads prepared records
-> matcher and scoring evaluate query matches
-> service ranks and returns top five AutoCompleteData results
-> CLI displays results
```

The implemented search is currently a linear scan over prepared records. The
planned optimized n-gram index is not implemented yet.

## Public Modules

- `autocomplete.normalization.normalize_text(text: str) -> str`
- `autocomplete.loader.iter_sentence_records(path: str | PathLike[str]) -> Iterator[SentenceRecord]`
- `autocomplete.loader.load_sentence_records(path: str | PathLike[str]) -> list[SentenceRecord]`
- `autocomplete.index.build_index(records: Iterable[SentenceRecord]) -> PreparedSentenceIndex`
- `autocomplete.index.save_index(data: PreparedSentenceIndex, path: str | PathLike[str]) -> None`
- `autocomplete.index.load_index(path: str | PathLike[str]) -> PreparedSentenceIndex`
- `autocomplete.matcher.find_best_match_score(normalized_prefix: str, normalized_sentence: str) -> int | None`
- `autocomplete.service.initialize(index_path: Path) -> None`
- `autocomplete.service.get_best_k_completions(prefix: str) -> list[AutoCompleteData]`
- `autocomplete.cli.run_cli() -> None`

## Data Model

`SentenceRecord` stores:

- `original_text`
- `normalized_text`
- `source_path`
- `line_number`

`line_number` is currently one-based: the first physical line in each source
file is line 1. Blank, whitespace-only, and punctuation-only lines still count
toward physical line numbers even when they are skipped as records.

`AutoCompleteData` stores:

- `completed_sentence`
- `source_text`
- `offset`
- `score`

The service maps `SentenceRecord.original_text` to
`AutoCompleteData.completed_sentence`, `SentenceRecord.source_path` to
`AutoCompleteData.source_text`, and `SentenceRecord.line_number` to
`AutoCompleteData.offset`.

## Build a Prepared Index

There is not yet a dedicated offline `scripts/build_index.py` command. For now,
build a prepared index with a short Python command:

```bash
PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from autocomplete.loader import load_sentence_records; from autocomplete.index import build_index, save_index; records = load_sentence_records(Path('data/raw')); save_index(build_index(records), Path('data/prepared/autocomplete-index.json'))"
```

## Run the CLI

After building a prepared index:

```bash
.venv/bin/python scripts/run_autocomplete.py data/prepared/autocomplete-index.json
```

The CLI keeps appending entered text to the current query. Enter `#` to reset
the current query.

## Run Tests

```bash
.venv/bin/python -m pytest -q
```

The tests use small fixtures under `tests/fixtures/` and do not require the full
supplied corpus.

"""Recursive UTF-8 text loading for the autocomplete corpus."""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import Iterator, List

from autocomplete.models import SentenceRecord
from autocomplete.normalization import normalize_text


PathInput = str | PathLike[str]


def _coerce_path(path: PathInput) -> Path:
    if not isinstance(path, (str, PathLike)):
        raise TypeError("path must be a str or pathlib.Path-compatible object")
    return Path(path)


def iter_text_files(path: PathInput) -> Iterator[Path]:
    """Yield `.txt` files from `path` in deterministic sorted order.

    `path` may point to a single `.txt` file or a directory. Missing paths raise
    `FileNotFoundError`. Non-`.txt` files are ignored.
    """

    source = _coerce_path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    if source.is_file():
        if source.suffix == ".txt":
            yield source
        return
    if not source.is_dir():
        return

    for text_file in sorted(
        (candidate for candidate in source.rglob("*.txt") if candidate.is_file()),
        key=lambda candidate: str(candidate),
    ):
        yield text_file


def iter_sentence_records(path: PathInput, *, errors: str = "strict") -> Iterator[SentenceRecord]:
    """Yield sentence records from UTF-8 `.txt` files under `path`.

    Lines are decoded as UTF-8. The default strict error policy raises
    `UnicodeDecodeError` for invalid input instead of silently changing corpus
    text. Empty, whitespace-only, and normalization-empty lines are skipped, but
    physical line numbers remain one-based and include skipped lines.
    """

    for text_file in iter_text_files(path):
        with text_file.open("r", encoding="utf-8", errors=errors) as file_obj:
            for line_number, raw_line in enumerate(file_obj, start=1):
                original_text = raw_line.rstrip("\r\n")
                normalized_text = normalize_text(original_text)
                if not normalized_text:
                    continue
                yield SentenceRecord(
                    original_text=original_text,
                    normalized_text=normalized_text,
                    source_path=str(text_file),
                    line_number=line_number,
                )


def load_sentence_records(path: PathInput, *, errors: str = "strict") -> List[SentenceRecord]:
    """Return all sentence records loaded from `path`."""

    return list(iter_sentence_records(path, errors=errors))

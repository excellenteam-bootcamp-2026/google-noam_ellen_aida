"""Build, save, and load prepared autocomplete sentence indexes."""

from __future__ import annotations

import json
from array import array
from json import JSONDecodeError
from os import PathLike
from pathlib import Path
from typing import Any, Dict, Iterable

from autocomplete.models import (
    NGramInvertedIndex,
    PreparedSentenceIndex,
    SentenceRecord,
)
from autocomplete.ngram import build_ngram_index


INDEX_FORMAT = "autocomplete-index"
INDEX_VERSION = 2
LEGACY_INDEX_VERSION = 1
PathInput = str | PathLike[str]


def build_index(records: Iterable[SentenceRecord]) -> PreparedSentenceIndex:
    """Build prepared autocomplete data from sentence records."""

    prepared_records = tuple(records)
    for record in prepared_records:
        _validate_record(record)
    return PreparedSentenceIndex(
        records=prepared_records,
        ngram_index=build_ngram_index(prepared_records),
    )


def save_index(data: PreparedSentenceIndex, path: PathInput) -> None:
    """Save prepared autocomplete data to a deterministic UTF-8 JSON file."""

    target = _coerce_path(path)
    payload = _data_to_payload(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        handle.write("\n")


def load_index(path: PathInput) -> PreparedSentenceIndex:
    """Load prepared autocomplete data from a UTF-8 JSON index file."""

    source = _coerce_path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except JSONDecodeError as exc:
        raise ValueError(f"Invalid index JSON: {exc.msg}") from exc

    return _payload_to_data(payload)


def _coerce_path(path: PathInput) -> Path:
    if not isinstance(path, (str, PathLike)):
        raise TypeError("path must be a str or pathlib.Path-compatible object")
    return Path(path)


def _data_to_payload(data: PreparedSentenceIndex) -> Dict[str, Any]:
    if not isinstance(data, PreparedSentenceIndex):
        raise TypeError("save_index() expects PreparedSentenceIndex")

    ngram_index = data.ngram_index or build_ngram_index(data.records)
    return {
        "format": INDEX_FORMAT,
        "version": INDEX_VERSION,
        "ngram_index": _ngram_index_to_payload(ngram_index),
        "records": [_record_to_payload(record) for record in data.records],
    }


def _ngram_index_to_payload(index: NGramInvertedIndex | None) -> Dict[str, Any]:
    if index is None:
        raise TypeError("NGramInvertedIndex payload cannot be built from None")
    return {
        "min_query_length": index.min_query_length,
        "ngram_sizes": list(index.ngram_sizes),
        "postings": {
            str(size): {
                gram: list(record_ids)
                for gram, record_ids in sorted(size_postings.items())
            }
            for size, size_postings in sorted(index.postings.items())
        },
    }


def _record_to_payload(record: SentenceRecord) -> Dict[str, Any]:
    _validate_record(record)
    return {
        "line_number": record.line_number,
        "normalized_text": record.normalized_text,
        "original_text": record.original_text,
        "source_path": record.source_path,
    }


def _validate_record(record: SentenceRecord) -> None:
    if not isinstance(record, SentenceRecord):
        raise TypeError("index records must be SentenceRecord instances")
    if not isinstance(record.original_text, str):
        raise TypeError("SentenceRecord original_text must be a string")
    if not isinstance(record.normalized_text, str):
        raise TypeError("SentenceRecord normalized_text must be a string")
    if not isinstance(record.source_path, str):
        raise TypeError("SentenceRecord source_path must be a string")
    if type(record.line_number) is not int or record.line_number < 1:
        raise TypeError("SentenceRecord line_number must be a positive integer")


def _payload_to_data(payload: Any) -> PreparedSentenceIndex:
    if not isinstance(payload, dict):
        raise ValueError("Index payload must be a JSON object")
    unexpected_fields = set(payload).difference(
        {"format", "version", "records", "ngram_index"}
    )
    if unexpected_fields:
        unexpected = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"Index payload has unexpected field(s): {unexpected}")
    if payload.get("format") != INDEX_FORMAT:
        raise ValueError("Unsupported index format")
    if type(payload.get("version")) is not int:
        raise ValueError("Unsupported index version")
    version = payload["version"]
    if version not in (LEGACY_INDEX_VERSION, INDEX_VERSION):
        raise ValueError("Unsupported index version")

    records_payload = payload.get("records")
    if not isinstance(records_payload, list):
        raise ValueError("Index payload must contain a records list")

    records = [_payload_to_record(record_payload) for record_payload in records_payload]
    prepared_records = tuple(records)
    if version == LEGACY_INDEX_VERSION:
        return PreparedSentenceIndex(
            records=prepared_records,
            ngram_index=build_ngram_index(prepared_records),
        )

    return PreparedSentenceIndex(
        records=prepared_records,
        ngram_index=_payload_to_ngram_index(
            payload.get("ngram_index"),
            record_count=len(prepared_records),
        ),
    )


def _payload_to_ngram_index(
    payload: Any,
    *,
    record_count: int,
) -> NGramInvertedIndex:
    if not isinstance(payload, dict):
        raise ValueError("Index payload must contain an ngram_index object")
    unexpected_fields = set(payload).difference(
        {"min_query_length", "ngram_sizes", "postings"}
    )
    if unexpected_fields:
        unexpected = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"ngram_index has unexpected field(s): {unexpected}")

    min_query_length = payload.get("min_query_length")
    if type(min_query_length) is not int or min_query_length < 1:
        raise ValueError("ngram_index min_query_length must be a positive integer")

    ngram_sizes = payload.get("ngram_sizes")
    if (
        not isinstance(ngram_sizes, list)
        or not ngram_sizes
        or any(type(size) is not int or size < 1 for size in ngram_sizes)
    ):
        raise ValueError("ngram_index ngram_sizes must be positive integers")

    postings_payload = payload.get("postings")
    if not isinstance(postings_payload, dict):
        raise ValueError("ngram_index postings must be an object")

    postings: dict[int, dict[str, array]] = {}
    for size in ngram_sizes:
        size_key = str(size)
        size_postings_payload = postings_payload.get(size_key)
        if not isinstance(size_postings_payload, dict):
            raise ValueError(f"ngram_index postings missing size {size_key}")
        size_postings: dict[str, array] = {}
        for gram, record_ids_payload in size_postings_payload.items():
            if not isinstance(gram, str) or len(gram) != size:
                raise ValueError("ngram_index posting gram has invalid size")
            size_postings[gram] = _payload_to_posting_ids(
                record_ids_payload,
                record_count=record_count,
            )
        postings[size] = dict(sorted(size_postings.items()))

    return NGramInvertedIndex(
        ngram_sizes=tuple(ngram_sizes),
        min_query_length=min_query_length,
        postings=postings,
    )


def _payload_to_posting_ids(
    payload: Any,
    *,
    record_count: int,
) -> array:
    if not isinstance(payload, list):
        raise ValueError("ngram_index posting IDs must be a list")
    posting = array("I")
    previous = -1
    for record_id in payload:
        if type(record_id) is not int:
            raise ValueError("ngram_index posting IDs must be integers")
        if record_id <= previous:
            raise ValueError("ngram_index posting IDs must be sorted and unique")
        if record_id < 0 or record_id >= record_count:
            raise ValueError("ngram_index posting ID out of range")
        posting.append(record_id)
        previous = record_id
    return posting


def _payload_to_record(payload: Any) -> SentenceRecord:
    if not isinstance(payload, dict):
        raise ValueError("Index record must be a JSON object")

    required_fields = {
        "line_number",
        "normalized_text",
        "original_text",
        "source_path",
    }
    missing_fields = required_fields.difference(payload)
    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise ValueError(f"Index record is missing required field(s): {missing}")
    unexpected_fields = set(payload).difference(required_fields)
    if unexpected_fields:
        unexpected = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"Index record has unexpected field(s): {unexpected}")

    original_text = payload["original_text"]
    normalized_text = payload["normalized_text"]
    source_path = payload["source_path"]
    line_number = payload["line_number"]

    if not isinstance(original_text, str):
        raise ValueError("Index record original_text must be a string")
    if not isinstance(normalized_text, str):
        raise ValueError("Index record normalized_text must be a string")
    if not isinstance(source_path, str):
        raise ValueError("Index record source_path must be a string")
    if type(line_number) is not int or line_number < 1:
        raise ValueError("Index record line_number must be a positive integer")

    return SentenceRecord(
        original_text=original_text,
        normalized_text=normalized_text,
        source_path=source_path,
        line_number=line_number,
    )

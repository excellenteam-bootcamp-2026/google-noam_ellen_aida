"""Build, save, and load prepared autocomplete sentence indexes."""

from __future__ import annotations

import json
from json import JSONDecodeError
from os import PathLike
from pathlib import Path
from typing import Any, Dict, Iterable

from autocomplete.models import PreparedSentenceIndex, SentenceRecord


INDEX_FORMAT = "autocomplete-index"
INDEX_VERSION = 1
PathInput = str | PathLike[str]


def build_index(records: Iterable[SentenceRecord]) -> PreparedSentenceIndex:
    """Build prepared autocomplete data from sentence records."""

    prepared_records = tuple(records)
    for record in prepared_records:
        _validate_record(record)
    return PreparedSentenceIndex(records=prepared_records)


def save_index(data: PreparedSentenceIndex, path: PathInput) -> None:
    """Save prepared autocomplete data to a deterministic UTF-8 JSON file."""

    target = _coerce_path(path)
    payload = _data_to_payload(data)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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

    return {
        "format": INDEX_FORMAT,
        "version": INDEX_VERSION,
        "records": [_record_to_payload(record) for record in data.records],
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
    unexpected_fields = set(payload).difference({"format", "version", "records"})
    if unexpected_fields:
        unexpected = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"Index payload has unexpected field(s): {unexpected}")
    if payload.get("format") != INDEX_FORMAT:
        raise ValueError("Unsupported index format")
    if type(payload.get("version")) is not int or payload["version"] != INDEX_VERSION:
        raise ValueError("Unsupported index version")

    records_payload = payload.get("records")
    if not isinstance(records_payload, list):
        raise ValueError("Index payload must contain a records list")

    records = [_payload_to_record(record_payload) for record_payload in records_payload]
    return PreparedSentenceIndex(records=tuple(records))


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

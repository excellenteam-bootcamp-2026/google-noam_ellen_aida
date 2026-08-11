# Phase A Data Flow

Phase A converts local raw text files into a prepared sentence index:

```text
raw text files
-> recursive loader
-> original and normalized SentenceRecord objects
-> prepared index
-> future matching/service modules
```

The loader accepts a file or directory path as `str` or `pathlib.Path`-compatible input. Directories are searched recursively for `.txt` files only, and files are processed in deterministic sorted-path order. Each physical line is treated as a possible sentence. Empty, whitespace-only, and normalization-empty lines are skipped as records, but they still count for one-based `line_number` values. The first physical line in each source file is line 1. This implementation does not use byte or character offsets.

Sentence text is read as UTF-8 with strict decoding. Invalid UTF-8 raises `UnicodeDecodeError` so corpus problems are visible instead of silently changing data.

Normalization uses `str.lower()`, replaces Unicode punctuation with spaces, collapses consecutive whitespace into one regular space, and trims leading/trailing whitespace. Punctuation is replaced with spaces rather than deleted so word boundaries are preserved for inputs such as hyphenated words or punctuation between words.

The prepared index is JSON and is represented in Python by `PreparedSentenceIndex`, not by the assignment result model `AutoCompleteData`. It uses explicit `SentenceRecord` fields, deterministic formatting, UTF-8 output, and validation on load. JSON is inspectable and does not execute code during loading, while remaining simple to replace with another format in a later phase if required. Later result creation should map `SentenceRecord.source_path` to `AutoCompleteData.source_text` and the one-based `SentenceRecord.line_number` to `AutoCompleteData.offset`.

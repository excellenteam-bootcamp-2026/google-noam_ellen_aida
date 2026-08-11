"""Text normalization rules used before autocomplete matching."""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Return a lowercase, punctuation-free, whitespace-normalized string.

    Unicode punctuation characters are replaced with spaces rather than removed
    so words separated by punctuation do not merge. Case is normalized with
    `str.lower()`. Non-string values raise `TypeError`.
    """

    if not isinstance(text, str):
        raise TypeError("normalize_text() expects a str")

    without_punctuation = "".join(
        " " if unicodedata.category(character).startswith("P") else character
        for character in text
    )
    normalized_space = _WHITESPACE_RE.sub(" ", without_punctuation)
    return normalized_space.strip().lower()

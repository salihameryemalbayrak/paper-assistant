"""Text normalization helpers for PDF-extracted and Turkish text.

Two separate problems are handled here:

1. PDF extraction artifacts: typographic ligatures ("ﬁ" as one character),
   soft hyphens and zero-width characters that are invisible but break
   search, and the same letter encoded in two ways (precomposed "ş" vs
   "s" + combining cedilla). NFC normalization unifies the latter.

2. Turkish casing: Python's default lower() is language-neutral, so
   "I".lower() == "i" (Turkish expects "ı") and "İ".lower() == "i̇"
   ("i" + a combining dot, two characters). turkish_lower() fixes both.
"""

import re
import unicodedata

# Characters replaced (or removed) after NFC normalization.
_REPLACEMENTS = str.maketrans(
    {
        "ﬀ": "ff",  # ﬀ
        "ﬁ": "fi",  # ﬁ
        "ﬂ": "fl",  # ﬂ
        "ﬃ": "ffi",  # ﬃ
        "ﬄ": "ffl",  # ﬄ
        "­": "",  # soft hyphen
        "​": "",  # zero-width space
        "﻿": "",  # byte order mark
        " ": " ",  # non-breaking space
    }
)
_HORIZONTAL_SPACE = re.compile(r"[ \t]+")


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC), fix PDF artifacts and collapse repeated spaces.

    Newlines are kept: paragraph and line structure matters for chunking.
    NFKC is deliberately not used, because it would also rewrite characters
    that carry meaning in papers (e.g. superscript "²" -> "2").
    """
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_REPLACEMENTS)
    text = _HORIZONTAL_SPACE.sub(" ", text)
    return text.strip()


def turkish_lower(text: str) -> str:
    """Lowercase with Turkish rules: I -> ı and İ -> i."""
    return text.replace("I", "ı").replace("İ", "i").lower()

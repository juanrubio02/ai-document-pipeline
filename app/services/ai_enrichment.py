from __future__ import annotations

import re
import unicodedata
from collections import Counter

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "not",
    "but",
    "you",
    "your",
    "our",
    "their",
    "into",
    "about",
    "after",
    "before",
    "under",
    "between",
    "through",
    "document",
    "documents",
    "text",
    "file",
    "para",
    "con",
    "por",
    "una",
    "uno",
    "del",
    "las",
    "los",
    "que",
    "como",
    "pero",
    "sus",
    "sin",
    "sobre",
    "entre",
    "desde",
    "hasta",
    "este",
    "esta",
    "estos",
    "estas",
    "ese",
    "esa",
    "esos",
    "esas",
    "documento",
    "archivo",
    "texto",
}

RESUME_HINTS = {"resume", "curriculum", "curriculum vitae", "cv"}
INVOICE_HINTS = {"invoice", "factura", "subtotal", "vat", "iva", "billing", "due date", "importe"}
CONTRACT_HINTS = {"contract", "agreement", "contrato", "clause", "clausula", "parties", "terms"}


def detect_document_type(filename: str, content_type: str | None, text: str) -> str:
    source = " ".join(
        [
            (filename or "").lower(),
            (content_type or "").lower(),
            _normalize_text(text),
        ]
    )

    if any(hint in source for hint in RESUME_HINTS):
        return "resume"
    if any(hint in source for hint in INVOICE_HINTS):
        return "invoice"
    if any(hint in source for hint in CONTRACT_HINTS):
        return "contract"
    return "generic"


def extract_keywords(text: str, max_keywords: int = 8) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []

    words = re.findall(r"[a-z]{3,}", normalized)
    if not words:
        return []

    filtered = [word for word in words if word not in STOPWORDS]
    if not filtered:
        return []

    counts = Counter(filtered)
    first_seen: dict[str, int] = {}
    for index, word in enumerate(filtered):
        first_seen.setdefault(word, index)

    sorted_words = sorted(
        counts.items(),
        key=lambda item: (-item[1], first_seen[item[0]], item[0]),
    )
    return [word for word, _count in sorted_words[:max_keywords]]


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    ascii_text = unicodedata.normalize("NFKD", lowered).encode("ascii", "ignore").decode("ascii")
    return ascii_text

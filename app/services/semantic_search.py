from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata

EMBEDDING_DIMENSIONS = 256
MIN_TOKEN_LENGTH = 3
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "have",
    "has",
    "into",
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
    "document",
    "documents",
    "documento",
    "documentos",
    "text",
    "texto",
    "file",
    "archivo",
}


def generate_embedding(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    normalized = _normalize_text(text)
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", normalized)
        if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS
    ]
    if not tokens:
        return [0.0] * dimensions

    vector = [0.0] * dimensions
    for token in tokens:
        index = _hash_token(token, dimensions)
        vector[index] += 1.0

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return [0.0] * dimensions

    return [value / norm for value in vector]


def serialize_embedding(embedding: list[float]) -> str:
    return json.dumps(embedding, separators=(",", ":"))


def deserialize_embedding(value: str) -> list[float]:
    loaded = json.loads(value)
    return [float(item) for item in loaded]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(0.0, sum(a * b for a, b in zip(left, right)))


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower()
    ascii_text = unicodedata.normalize("NFKD", lowered).encode("ascii", "ignore").decode("ascii")
    return ascii_text


def _hash_token(token: str, dimensions: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % dimensions

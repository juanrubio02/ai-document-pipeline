from __future__ import annotations

import re

MAX_SUMMARY_CHARS = 500
SHORT_TEXT_THRESHOLD = 200


def generate_summary(text: str) -> str:
    """
    Generate a short summary from document text using a simple heuristic:
    - For short text (< 200 chars), return original text.
    - Otherwise, return first 2-3 sentences.
    - Always cap output at 500 chars.
    """
    content = (text or "").strip()
    if not content:
        return ""

    if len(content) < SHORT_TEXT_THRESHOLD:
        return content[:MAX_SUMMARY_CHARS]

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", content) if s.strip()]
    if not sentences:
        return content[:MAX_SUMMARY_CHARS]

    summary = " ".join(sentences[:3])
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[:MAX_SUMMARY_CHARS].rstrip()
    return summary

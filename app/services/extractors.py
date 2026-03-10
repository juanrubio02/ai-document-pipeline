from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def extract_text_from_file(path: str, filename: str, content_type: str | None = None) -> str:
    """
    Extract text from a stored file based on extension (primary) and content_type (fallback).
    Raises ValueError when file type is unsupported or text is not extractable.
    """
    extension = _detect_extension(filename=filename, content_type=content_type)

    if extension in {".txt", ".md"}:
        return _extract_text_utf8(path)
    if extension == ".pdf":
        return _extract_pdf_text(path)
    if extension == ".docx":
        return _extract_docx_text(path)

    raise ValueError(
        f"Unsupported file type: extension={extension or 'unknown'}, "
        "supported=.txt,.md,.pdf,.docx"
    )


def _detect_extension(filename: str, content_type: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in SUPPORTED_EXTENSIONS:
        return ext

    by_content_type = {
        "text/plain": ".txt",
        "text/markdown": ".md",
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }
    return by_content_type.get((content_type or "").lower(), ext)


def _extract_text_utf8(path: str) -> str:
    with open(path, "rb") as file:
        return file.read().decode("utf-8", errors="replace")


def _extract_pdf_text(path: str) -> str:
    try:
        import fitz
    except ImportError as e:
        raise ValueError("PDF extraction dependency is missing (install pymupdf)") from e

    chunks: list[str] = []
    with fitz.open(path) as pdf:
        for page in pdf:
            chunks.append(page.get_text("text"))

    text = "\n".join(chunks).strip()
    if not text:
        raise ValueError("No extractable text found in PDF (possibly scanned or image-only)")
    return text


def _extract_docx_text(path: str) -> str:
    try:
        from docx import Document as DocxDocument
    except ImportError as e:
        raise ValueError("DOCX extraction dependency is missing (install python-docx)") from e

    doc = DocxDocument(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text]
    text = "\n".join(paragraphs).strip()
    if not text:
        raise ValueError("No extractable text found in DOCX")
    return text

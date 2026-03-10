from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.services.extractors import extract_text_from_file


class ExtractorsTests(unittest.TestCase):
    def test_extract_txt_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.txt"
            path.write_bytes("hola mundo".encode("utf-8"))

            text = extract_text_from_file(str(path), "note.txt", "text/plain")

            self.assertEqual(text, "hola mundo")

    def test_extract_md_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "readme.md"
            path.write_bytes("# titulo".encode("utf-8"))

            text = extract_text_from_file(str(path), "readme.md", "text/markdown")

            self.assertEqual(text, "# titulo")

    def test_unsupported_extension_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "archive.zip"
            path.write_bytes(b"fake")

            with self.assertRaises(ValueError) as ctx:
                extract_text_from_file(str(path), "archive.zip", "application/zip")

        self.assertIn("Unsupported file type", str(ctx.exception))

    def test_extract_pdf_with_embedded_text(self) -> None:
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.pdf"
            pdf = fitz.open()
            page = pdf.new_page()
            page.insert_text((72, 72), "hello from pdf")
            pdf.save(str(path))
            pdf.close()

            text = extract_text_from_file(str(path), "sample.pdf", "application/pdf")

            self.assertIn("hello from pdf", text.lower())

    def test_extract_docx_text(self) -> None:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            self.skipTest("python-docx not installed")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.docx"
            doc = DocxDocument()
            doc.add_paragraph("hello from docx")
            doc.save(str(path))

            text = extract_text_from_file(
                str(path),
                "sample.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

            self.assertIn("hello from docx", text.lower())


if __name__ == "__main__":
    unittest.main()

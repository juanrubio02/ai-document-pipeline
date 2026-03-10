from __future__ import annotations

import unittest

from app.services.ai_enrichment import detect_document_type, extract_keywords


class AIEnrichmentTests(unittest.TestCase):
    def test_detect_document_type_resume_from_filename(self) -> None:
        result = detect_document_type("juan-cv.pdf", "application/pdf", "Perfil profesional")
        self.assertEqual(result, "resume")

    def test_detect_document_type_invoice_from_text(self) -> None:
        text = "Factura numero 123. Subtotal 100. IVA 21. Total 121."
        result = detect_document_type("doc.pdf", "application/pdf", text)
        self.assertEqual(result, "invoice")

    def test_detect_document_type_contract_from_text(self) -> None:
        text = "This contract defines the parties and the terms of the agreement."
        result = detect_document_type("agreement.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", text)
        self.assertEqual(result, "contract")

    def test_extract_keywords_returns_ranked_unique_terms(self) -> None:
        text = (
            "Python backend invoice backend analytics analytics analytics "
            "pipeline document processing python service"
        )
        result = extract_keywords(text, max_keywords=5)
        self.assertIn("analytics", result)
        self.assertIn("backend", result)
        self.assertEqual(len(result), len(set(result)))
        self.assertLessEqual(len(result), 5)

    def test_extract_keywords_filters_basic_stopwords(self) -> None:
        text = "the and para con invoice contract backend service"
        result = extract_keywords(text, max_keywords=8)
        self.assertNotIn("the", result)
        self.assertNotIn("and", result)
        self.assertNotIn("para", result)
        self.assertIn("invoice", result)


if __name__ == "__main__":
    unittest.main()

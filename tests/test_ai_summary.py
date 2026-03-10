from __future__ import annotations

import unittest

from app.services.ai_summary import generate_summary


class AISummaryTests(unittest.TestCase):
    def test_short_text_returns_original(self) -> None:
        text = "Texto corto para probar resumen."
        self.assertEqual(generate_summary(text), text)

    def test_long_text_returns_first_sentences_and_is_capped(self) -> None:
        text = (
            "Primera frase importante. "
            "Segunda frase relevante. "
            "Tercera frase complementaria. "
            "Cuarta frase que no debería entrar normalmente. "
            "Esta frase adicional existe para superar claramente el umbral de 200 caracteres y activar "
            "la lógica de resumen por frases sin depender de casos límite en longitud total del texto."
        )
        summary = generate_summary(text)

        self.assertIn("Primera frase importante.", summary)
        self.assertIn("Segunda frase relevante.", summary)
        self.assertIn("Tercera frase complementaria.", summary)
        self.assertNotIn("Cuarta frase", summary)
        self.assertLessEqual(len(summary), 500)


if __name__ == "__main__":
    unittest.main()

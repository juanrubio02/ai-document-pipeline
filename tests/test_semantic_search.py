from __future__ import annotations

import unittest

from app.services.semantic_search import (
    cosine_similarity,
    deserialize_embedding,
    generate_embedding,
    serialize_embedding,
)


class SemanticSearchTests(unittest.TestCase):
    def test_generate_embedding_is_deterministic(self) -> None:
        text = "python backend docker pipeline"
        first = generate_embedding(text)
        second = generate_embedding(text)
        self.assertEqual(first, second)

    def test_serialization_round_trip(self) -> None:
        embedding = generate_embedding("semantic search for backend documents")
        restored = deserialize_embedding(serialize_embedding(embedding))
        self.assertEqual(embedding, restored)

    def test_similarity_is_higher_for_related_texts(self) -> None:
        query = generate_embedding("python backend docker")
        related = generate_embedding("python backend api with docker deployment")
        unrelated = generate_embedding("invoice subtotal vat billing amount")

        self.assertGreater(cosine_similarity(query, related), cosine_similarity(query, unrelated))


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from tests.fakes import TEST_SETTINGS
from voc_rag.llm import E5Embeddings
from voc_rag.reranker import CrossEncoderReranker
from voc_rag.schemas import ReviewFilters
from voc_rag.vector_store import FaissReviewStore, to_chroma_filter

DOCUMENTS = pd.DataFrame({
    "review_id": ["a", "b", "c", "d"],
    "text": ["chegou atrasado", "veio quebrado", "ótimo produto", "não recebi"],
    "score": [1, 2, 5, 1],
    "state": ["SP", "RJ", "SP", None],
})
VECTORS = {
    "chegou atrasado": [1.0, 0.0, 0.0], "veio quebrado": [0.0, 1.0, 0.0],
    "ótimo produto": [0.9, 0.1, 0.0], "não recebi": [0.7, 0.0, 0.7],
}


class FakeDocumentEmbeddings:
    def embed_documents(self, texts):
        return [VECTORS[text] for text in texts]

    def embed_query(self, text):
        return VECTORS[text]


class FaissStoreTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        self.settings = replace(TEST_SETTINGS, faiss_dir=root / "faiss", processed_dir=root)
        DOCUMENTS.to_parquet(self.settings.documents_path, index=False)
        FaissReviewStore.build(self.settings, FakeDocumentEmbeddings(), DOCUMENTS)
        self.store = FaissReviewStore.load(self.settings, FakeDocumentEmbeddings())

    def tearDown(self):
        self.folder.cleanup()

    def test_search_is_ranked_by_cosine(self):
        self.assertEqual(self.store.search([1.0, 0.0, 0.0], 3, ReviewFilters.empty()), ["a", "c", "d"])

    def test_prefilter_keeps_only_the_slice_even_when_it_is_far_from_the_query(self):
        # "b" é o vizinho mais distante da consulta, mas é a única avaliação com nota até 2 do RJ.
        filters = ReviewFilters.empty().model_copy(update={"max_score": 2, "states": ["RJ"]})
        self.assertEqual(self.store.search([1.0, 0.0, 0.0], 10, filters), ["b"])

    def test_empty_slice_returns_nothing(self):
        filters = ReviewFilters.empty().model_copy(update={"states": ["AM"]})
        self.assertEqual(self.store.search([1.0, 0.0, 0.0], 10, filters), [])

    def test_fetch_reconstructs_normalized_vectors_and_metadata(self):
        found = self.store.fetch(["d", "inexistente"])
        text, metadata, vector = found["d"]
        self.assertEqual(list(found), ["d"])
        self.assertEqual(text, "não recebi")
        self.assertEqual(metadata, {"review_id": "d", "score": 1})
        self.assertIsInstance(metadata["score"], int)
        np.testing.assert_allclose(vector, np.array([0.7, 0.0, 0.7]) / np.linalg.norm([0.7, 0.0, 0.7]), rtol=1e-6)

    def test_load_rejects_an_index_from_another_base(self):
        DOCUMENTS.iloc[::-1].to_parquet(self.settings.documents_path, index=False)
        with self.assertRaises(RuntimeError):
            FaissReviewStore.load(self.settings, FakeDocumentEmbeddings())


class ChromaFilterTest(unittest.TestCase):
    def test_chroma_filter(self):
        empty = ReviewFilters.empty()
        self.assertIsNone(to_chroma_filter(empty))
        self.assertEqual(to_chroma_filter(empty.model_copy(update={"max_score": 2})), {"score": {"$lte": 2}})
        both = empty.model_copy(update={"max_score": 2, "states": ["SP"]})
        self.assertEqual(to_chroma_filter(both), {"$and": [{"score": {"$lte": 2}}, {"state": {"$in": ["SP"]}}]})


class RecordingEncoder:
    def __init__(self):
        self.texts = []

    def encode(self, texts, batch_size, normalize_embeddings, show_progress_bar):
        self.texts += texts
        return np.ones((len(texts), 2))

    def predict(self, pairs, show_progress_bar=False):
        self.texts += pairs
        return np.arange(len(pairs), dtype=float)


class LocalModelsTest(unittest.TestCase):
    def test_e5_uses_query_and_passage_prefixes(self):
        encoder = RecordingEncoder()
        embeddings = E5Embeddings("intfloat/multilingual-e5-small", encoder=encoder)
        embeddings.embed_query("atraso")
        embeddings.embed_documents(["chegou tarde"])
        self.assertEqual(encoder.texts, ["query: atraso", "passage: chegou tarde"])

    def test_other_local_models_get_plain_text(self):
        encoder = RecordingEncoder()
        E5Embeddings("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", encoder=encoder).embed_query("atraso")
        self.assertEqual(encoder.texts, ["atraso"])

    def test_cross_encoder_scores_every_pool_in_one_batch(self):
        encoder = RecordingEncoder()
        reranker = CrossEncoderReranker("fake", encoder=encoder)
        grades = reranker.grade("p", "nenhum", ["q1", "q2", "q3"], [["a", "b"], [], ["c"]])
        self.assertEqual(grades, [[0.0, 1.0], [], [2.0]])
        self.assertEqual(encoder.texts, [("q1", "a"), ("q1", "b"), ("q3", "c")])
        self.assertAlmostEqual(reranker.score(0.0, 0.9), 0.5)


if __name__ == "__main__":
    unittest.main()

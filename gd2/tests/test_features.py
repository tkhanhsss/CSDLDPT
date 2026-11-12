import tempfile
import unittest
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from gd2.src.build_features import load_gd1
from gd2.src.features import (build_features, load_features, max_sparse_difference,
                              save_features, validate_features, vectorizer_parameters)
from gd2.src.preprocess import content_tokens, raw_tokens, token_trace


class FeaturesTests(unittest.TestCase):
    def test_preprocessing_matches_gd1_on_edge_cases(self):
        original = load_gd1()
        text = "John’s JOHN‘S Johnʼs didn't won’t Chapter I IV LX LXI A x 123 running relational skies dying café co-operate"
        self.assertEqual(content_tokens(text), original.content_tokens(text))
        self.assertEqual(content_tokens("John’s Johnʼs running RUNNING"), ["john", "john", "run", "run"])
        self.assertEqual(content_tokens("the CHAPTER LX didn't x 123"), [])
        self.assertEqual(raw_tokens("John’s 42 dogs"), ["john's", "dogs"])
        self.assertEqual([row["decision"] for row in token_trace("x chapter dogs")],
                         ["short_base", "stopword", "kept"])

    def example(self):
        texts = ["apple apple orchard common rare", "apple orchard common", "apple orchard common",
                 "banana common", "banana common", "banana common"]
        documents = [{"row_index": i, "doc_id": i + 1, "filename": f"book_{i:04}.txt"}
                     for i in range(len(texts))]
        return texts, build_features(texts, documents)

    def test_df_boundaries_log_tf_and_l2_against_hand_calculation(self):
        texts, bundle = self.example()
        self.assertEqual(list(bundle.terms), ["appl", "banana", "orchard"])
        np.testing.assert_array_equal(bundle.df, [3, 3, 3])
        np.testing.assert_array_equal(bundle.counts.toarray()[0], [2, 0, 1])
        np.testing.assert_allclose(bundle.idf, np.log(7 / 4) + 1)
        raw = np.array([1 + np.log(2), 0, 1]) * (np.log(7 / 4) + 1)
        np.testing.assert_allclose(bundle.tfidf.toarray()[0], raw / np.linalg.norm(raw))
        self.assertEqual(validate_features(bundle)["zero_rows"], 0)
        reference = TfidfVectorizer(**vectorizer_parameters(load_gd1().content_tokens)).fit_transform(texts)
        self.assertLessEqual(max_sparse_difference(bundle.tfidf, reference), 1e-15)

    def test_zero_document_and_round_trip(self):
        texts = ["apple", "apple", "apple", "banana", "banana", "banana", "the chapter"]
        documents = [{"row_index": i, "doc_id": i + 1, "filename": f"book_{i:04}.txt"}
                     for i in range(len(texts))]
        bundle = build_features(iter(texts), documents)
        self.assertEqual(validate_features(bundle)["zero_rows"], 1)
        self.assertEqual(bundle.l2_raw[-1], 0)
        with tempfile.TemporaryDirectory() as directory:
            save_features(bundle, Path(directory))
            restored = load_features(Path(directory))
            validate_features(restored)
            self.assertEqual(max_sparse_difference(bundle.tfidf, restored.tfidf), 0)
            self.assertEqual(max_sparse_difference(bundle.counts, restored.counts), 0)

    def test_rejects_corrupt_weights_counts_and_mapping(self):
        _, bundle = self.example()
        bundle.tfidf.data[0] += 0.1
        with self.assertRaises(ValueError):
            validate_features(bundle)
        _, bundle = self.example()
        bundle.documents[0]["doc_id"] = 99
        with self.assertRaises(ValueError):
            validate_features(bundle)
        _, bundle = self.example()
        bundle.counts.data[0] = 0
        with self.assertRaises(ValueError):
            validate_features(bundle)


if __name__ == "__main__":
    unittest.main()

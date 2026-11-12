import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from gd2.src.database import DatabaseIndex
from gd2.src.features import build_features, max_sparse_difference, vectorizer_parameters
from gd2.src.search import detailed_token_trace, rank_scores, run, transform_query


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        corpus = self.root / "data/corpus"
        corpus.mkdir(parents=True)
        texts = ["apple apple orchard", "apple orchard", "apple orchard", "banana", "banana", "banana"]
        docs = []
        for i, text in enumerate(texts):
            path = corpus / f"book_{i:04}.txt"
            path.write_text(text, encoding="utf-8")
            docs.append({"row_index": i, "doc_id": i + 1, "filename": path.name,
                "relative_path": path.relative_to(self.root).as_posix(), "raw_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "title": "Test", "author_display": "Author", "label_code": "test"})
        self.bundle = build_features(texts, docs)
        self.index = DatabaseIndex({"build_id": "test"}, [], self.bundle)
        self.vocab = {term: i for i, term in enumerate(self.bundle.terms)}
        self.reference = TfidfVectorizer(**vectorizer_parameters()).fit(texts)

    def test_transform_matches_sklearn_with_repetitions_oov_and_empty(self):
        for query in ["apple APPLE orchard unknown", "the chapter I", "zzzzunknown", "banana’s banana"]:
            with self.subTest(query=query):
                q, _, _, _ = transform_query(query, self.vocab, self.bundle.idf)
                expected = self.reference.transform([query])
                self.assertLess(max_sparse_difference(q, expected), 1e-14)

    def test_ties_and_zero_scores_use_filename(self):
        docs = [{"filename": name} for name in ["c.txt", "b.txt", "a.txt", "d.txt"]]
        self.assertEqual(rank_scores(np.array([0., 1., 0., 0.]), docs).tolist(), [1, 2, 0, 3])
        self.assertEqual(rank_scores(np.ones(4), docs).tolist(), [2, 1, 0, 3])

    def test_trace_preserves_original_case_apostrophes_and_offsets(self):
        text = "John’s APPLES İ pear"
        rows = detailed_token_trace(text)
        self.assertEqual(rows[0]["original_token"], "John’s")
        self.assertEqual(rows[0]["token"], "john's")
        for row in rows:
            self.assertEqual(text[row["character_start"]:row["character_end"]], row["original_token"])
        self.assertEqual(rows[-1]["original_token"], "pear")

    def test_batch_loads_once_continues_errors_and_exports_trace(self):
        queries = []
        for i, data in enumerate([b"apple apple orchard", b"the chapter", b"123 !!!", b"", b"\xff", b"banana"]):
            folder = self.root / str(i)
            folder.mkdir()
            path = folder / "same.txt"
            path.write_bytes(data)
            queries.append(path)
        queries.append(self.root / "missing.txt")
        output = self.root / "output"
        with patch("gd2.src.search.load_database", return_value=self.index) as loader:
            code = run(queries, output, trace=True, corpus_root=self.root)
        self.assertEqual(code, 1)
        loader.assert_called_once()
        for n, expected in enumerate(["ok", "empty_vector", "error", "error", "error", "ok", "error"], 1):
            folder = output / f"Q{n:02}"
            result = json.loads((folder / "results.json").read_text())
            self.assertEqual(result["status"], expected)
            copies = list(folder.glob("*.txt"))
            self.assertEqual(len(copies), 3 if expected == "ok" else 0)
            for row in result["top3"]:
                self.assertEqual(hashlib.sha256((folder / row["copy_path"]).read_bytes()).hexdigest(), row["raw_sha256"])
        trace = json.loads((output / "Q01/trace_summary.json").read_text())
        self.assertTrue(all(row["absolute_error"] <= 1e-10 for row in trace["contributions"]))

    def test_changed_corpus_publishes_no_partial_copies(self):
        query = self.root / "query.txt"
        query.write_text("banana")
        (self.root / self.bundle.documents[4]["relative_path"]).write_text("changed")
        with patch("gd2.src.search.load_database", return_value=self.index):
            self.assertEqual(run([query], self.root / "out", corpus_root=self.root), 1)
        self.assertFalse(list((self.root / "out").rglob("*.txt")))

    def test_invalid_database_and_existing_output_do_not_write(self):
        output = self.root / "out"
        with patch("gd2.src.search.load_database", side_effect=ValueError("invalid database")):
            with self.assertRaises(ValueError):
                run([self.root / "query.txt"], output, corpus_root=self.root)
        self.assertFalse(output.exists())
        output.mkdir()
        with self.assertRaises(FileExistsError):
            run([], output, corpus_root=self.root)

    def test_default_output_omits_trace_and_empty_is_success(self):
        query = self.root / "query.txt"
        query.write_text("the chapter")
        with patch("gd2.src.search.load_database", return_value=self.index):
            self.assertEqual(run([query], self.root / "out", corpus_root=self.root), 0)
        self.assertFalse((self.root / "out/Q01/all_scores.csv").exists())


if __name__ == "__main__":
    unittest.main()

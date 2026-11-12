import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import numpy as np

from gd2.src.build_database import run, unique_rows
from gd2.src.database import connect, load_database, populate_database
from gd2.src.features import build_features, max_sparse_difference
from gd2.src.preprocess import CONFIG


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "documents.sqlite"
        texts = ["apple apple orchard", "apple orchard", "apple orchard", "banana", "banana", "banana"]
        rows = [{"doc_id": i + 1, "row_index": i, "filename": f"book_{i:04}.txt"} for i in range(6)]
        self.bundle = build_features(texts, rows)
        self.labels = [{"label_code": "example", "display_name": "Example fiction"}]
        self.documents = [{"doc_id": i + 1, "filename": row["filename"],
            "relative_path": "data/corpus/" + row["filename"],
            "raw_sha256": "a" * 64, "word_count": len(texts[i].split()),
            "label_code": "example", "title": "L’île — 'Book' " + str(i),
            "author_display": "Honoré de Balzac", "l2_raw": float(self.bundle.l2_raw[i])}
            for i, row in enumerate(rows)]
        self.info = {"build_id": "test", "created_at": "2026-11-04T00:00:00+07:00",
            "n_docs": 6, "n_terms": len(self.bundle.terms), "nnz": self.bundle.tfidf.nnz,
            "config_json": json.dumps(CONFIG), "versions_json": "{}", "corpus_manifest_sha256": "a" * 64,
            "preprocess_sha256": "b" * 64, "stopwords_sha256": "c" * 64,
            "p2_verification_sha256": "d" * 64, "source_hashes_json": "{}"}

    def populate(self):
        return populate_database(self.path, self.bundle, self.documents, self.labels, self.info)

    def test_round_trip_preserves_all_features_and_unicode(self):
        result = self.populate()
        self.assertEqual(result["p2_comparison"]["max_weight_difference"], 0)
        index = load_database(self.path)
        self.assertEqual(index.build_info["status"], "complete")
        self.assertEqual(max_sparse_difference(index.features.counts, self.bundle.counts), 0)
        self.assertEqual(max_sparse_difference(index.features.tfidf, self.bundle.tfidf), 0)
        np.testing.assert_array_equal(index.features.idf, self.bundle.idf)
        self.assertEqual(index.features.documents[0]["title"], self.documents[0]["title"])

    def test_constraints_and_readonly_connections(self):
        self.populate()
        with closing(connect(self.path)) as connection:
            cases = [("INSERT INTO document_terms VALUES (999,1,1,0.1)", ()),
                     ("UPDATE document_terms SET term_count=0 WHERE doc_id=1", ()),
                     ("UPDATE document_terms SET weight=-0.1 WHERE doc_id=1", ()),
                     ("INSERT INTO document_terms SELECT * FROM document_terms LIMIT 1", ()),
                     ("UPDATE documents SET filename='book_0000.txt' WHERE doc_id=2", ())]
            for sql, params in cases:
                with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(sql, params)
                connection.rollback()
        with closing(connect(self.path, readonly=True)) as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM document_terms")

    def test_failed_validation_rolls_back_schema_and_rows(self):
        with patch("gd2.src.database.validate_database", side_effect=ValueError("injected failure")):
            with self.assertRaisesRegex(ValueError, "injected failure"):
                self.populate()
        with closing(connect(self.path, readonly=True)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0], 0)
        with self.assertRaises(ValueError):
            load_database(self.path)

    def test_loader_rejects_incomplete_and_corrupt_builds(self):
        self.populate()
        with closing(connect(self.path)) as connection:
            connection.execute("UPDATE build_info SET status='building'")
            connection.commit()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            load_database(self.path)
        with closing(connect(self.path)) as connection:
            connection.execute("UPDATE build_info SET status='complete'")
            connection.execute("UPDATE document_terms SET weight=weight/2 WHERE doc_id=1")
            connection.commit()
        with self.assertRaises(ValueError):
            load_database(self.path)

    def test_existing_output_and_duplicate_metadata_are_rejected(self):
        self.path.write_bytes(b"existing user file")
        with self.assertRaises(FileExistsError):
            run(self.path, Path("does-not-exist"))
        self.assertEqual(self.path.read_bytes(), b"existing user file")
        with self.assertRaises(ValueError):
            unique_rows([{"filename": "one"}, {"filename": "one"}], "filename", {"one"})
        with self.assertRaises(ValueError):
            unique_rows([{"filename": "one"}], "filename", {"one", "two"})

    def test_search_loader_does_not_run_deep_audit(self):
        self.populate()
        with patch("gd2.src.database.validate_database", side_effect=AssertionError("deep audit called")):
            index = load_database(self.path)
        self.assertEqual(index.features.tfidf.shape, self.bundle.tfidf.shape)

    def test_configuration_notes_are_ignored_but_feature_changes_rejected(self):
        self.populate()
        config = json.loads(json.dumps(CONFIG))
        config.update(date="2030-01-01", note="Updated documentation", capture_versions={})
        config["corpus"]["directory"] = "another/location"
        with closing(connect(self.path)) as connection:
            connection.execute("UPDATE build_info SET config_json=?", (json.dumps(config),))
            connection.commit()
        load_database(self.path)
        config["tfidf"]["sublinear_tf"] = False
        with closing(connect(self.path)) as connection:
            connection.execute("UPDATE build_info SET config_json=?", (json.dumps(config),))
            connection.commit()
        with self.assertRaisesRegex(ValueError, "incompatible"):
            load_database(self.path)


if __name__ == "__main__":
    unittest.main()

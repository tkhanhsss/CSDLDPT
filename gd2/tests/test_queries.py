import tempfile
import unittest
from pathlib import Path

import numpy as np

from gd2.src.prepare_queries import extract, scan_overlap, window_hashes
from gd2.src.preprocess import raw_tokens


class QueryPreparationTests(unittest.TestCase):
    def source(self, body):
        return "License\r\n*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\r\n" + body + "\r\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\r\nLicense"

    def test_contiguous_extraction_preserves_quotes_and_crlf(self):
        body = "Opening John’s story.\r\n\r\n" + "word " * 997 + "ends."
        source = self.source(body)
        query, start, end, count, _ = extract(source, "Opening John’s")
        self.assertEqual(query, source[start:end])
        self.assertEqual(count, len(raw_tokens(query)))
        self.assertTrue(950 <= count <= 1050)
        self.assertIn("\r\n", query)

    def test_rejects_ambiguous_anchor_and_illustration(self):
        with self.assertRaisesRegex(ValueError, "exactly once"):
            extract(self.source("Anchor Anchor " + "word " * 1000 + "."), "Anchor")
        with self.assertRaisesRegex(ValueError, "non-narrative"):
            extract(self.source("Anchor " + "word " * 499 + "[Illustration] " + "word " * 499 + "."), "Anchor")

    def test_window_hashes_match_direct_formula(self):
        values = np.arange(1, 60, dtype=np.uint64)
        expected = []
        for start in range(len(values) - 12 + 1):
            h = 0
            for value in values[start:start + 12]:
                h = (h * 1_000_003 + int(value)) % (2 ** 64)
            expected.append(h)
        np.testing.assert_array_equal(window_hashes(values, 12), expected)

    def test_query_and_source_anchor_scan_detects_shared_run(self):
        tokens = ["term" + chr(97 + i // 26) + chr(97 + i % 26) for i in range(100)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "book.txt"
            path.write_text(" ".join(tokens[29:88]), encoding="utf-8")
            hits = scan_overlap({"Q01": tokens[29:59]}, {"Q01": tokens}, [path])["Q01"]
        self.assertTrue(hits["query_12gram_hits"])
        self.assertTrue(hits["source_30gram_hits"])
        self.assertEqual(hits["source_30gram_hits"][0]["source_token_offset"], 30)


if __name__ == "__main__":
    unittest.main()

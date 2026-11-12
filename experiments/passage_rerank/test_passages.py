"""Boundary and numerical checks for the isolated passage experiment."""
import unittest
import numpy as np

from experiments.passage_rerank.run import independent_cosine, windows, word_spans
from gd2.src.preprocess import raw_tokens
from gd2.src.search import transform_query


class PassageTests(unittest.TestCase):
    def test_tail_coverage_no_duplicate_window(self):
        for length in [1, 999, 1000, 1001, 1499, 1500, 1501, 2000, 2017]:
            text = ' '.join(['ship'] * length)
            spans = windows(text)
            self.assertEqual(spans[0]['word_start'], 1)
            self.assertEqual(spans[-1]['word_end'], length)
            self.assertEqual(len({s['word_start'] for s in spans}), len(spans))
            covered = set()
            for span in spans:
                self.assertEqual(len(raw_tokens(text[span['char_start']:span['char_end']])), min(1000, length))
                covered.update(range(span['word_start'], span['word_end'] + 1))
            self.assertEqual(covered, set(range(1, length + 1)))

    def test_unicode_offsets_and_apostrophes(self):
        text = '  İSTANBUL\r\nCaptain’s ship, sailor\'s story. '
        spans = word_spans(text)
        reconstructed = [token for start, end in spans for token in raw_tokens(text[start:end])]
        self.assertEqual(reconstructed, raw_tokens(text))

    def test_empty_and_invalid_windows(self):
        self.assertEqual(windows('123 !!!'), [])
        for width, stride in [(0, 1), (10, 0), (10, 11)]:
            with self.assertRaises(ValueError):
                windows('ship', width, stride)

    def test_cosine_formula_and_oov(self):
        vocabulary = {'ship': 0, 'sea': 1, 'garden': 2}
        idf = np.array([2.0, 3.0, 4.0])
        query = 'ship ship sea OOV'
        passage = 'ship garden garden OOV'
        q = transform_query(query, vocabulary, idf)[0]
        p = transform_query(passage, vocabulary, idf)[0]
        self.assertAlmostEqual(float((q @ p.T).toarray()[0, 0]),
                               independent_cosine(query, passage, vocabulary, idf), places=14)
        self.assertEqual(independent_cosine(query, 'unknownword', vocabulary, idf), 0)


if __name__ == '__main__':
    unittest.main()

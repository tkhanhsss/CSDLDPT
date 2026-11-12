import unittest

from gd2.src.evaluate import compute_metrics, validate_judgments


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.pairs = [{"pair_id": f"P{n:03}", "query_id": f"Q{(n-1)//3+1:02}", "rank": (n-1)%3+1}
                      for n in range(1, 37)]
        self.texts = {p["pair_id"]: ("The query describes a ship at sea.", "The sailor repairs the ship.") for p in self.pairs}
        self.rows = [{"pair_id": p["pair_id"], "reviewer": "Member A", "grade": "2",
                      "query_evidence": "a ship at sea", "document_evidence": "sailor repairs the ship",
                      "reason": "Both describe work aboard a ship."} for p in self.pairs]

    def test_missing_grades_are_pending_not_irrelevant(self):
        self.rows[0]["grade"] = ""
        scores, pending, names = validate_judgments(self.rows, self.pairs, self.texts)
        self.assertEqual(len(scores), 35)
        self.assertEqual(pending, ["P001"])
        self.assertEqual(names, {"member a"})
        with self.assertRaises(ValueError):
            compute_metrics(self.pairs, scores, scores, scores)

    def test_invalid_missing_or_fabricated_evidence_rejected(self):
        for field, value in [("grade", "3"), ("grade", "NaN"), ("reason", ""),
                             ("reviewer", ""), ("document_evidence", "a murder investigation")]:
            rows = [dict(r) for r in self.rows]
            rows[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate_judgments(rows, self.pairs, self.texts)

    def test_duplicate_pairs_and_mixed_reviewer_rejected(self):
        rows = [dict(r) for r in self.rows]
        rows[0]["pair_id"] = rows[1]["pair_id"]
        with self.assertRaises(ValueError):
            validate_judgments(rows, self.pairs, self.texts)
        rows = [dict(r) for r in self.rows]
        rows[0]["reviewer"] = "Another member"
        with self.assertRaises(ValueError):
            validate_judgments(rows, self.pairs, self.texts)

    def test_whitespace_in_verbatim_quotes_is_accepted(self):
        self.rows[0]["document_evidence"] = "sailor\nrepairs  the ship"
        scores, pending, _ = validate_judgments(self.rows, self.pairs, self.texts)
        self.assertEqual(len(scores), 36)
        self.assertFalse(pending)

    def test_grade_one_not_binary_relevant_and_denominator_fixed(self):
        consensus = {p["pair_id"]: int(p["rank"]) - 1 for p in self.pairs}
        second = dict(consensus)
        second["P001"] = 2
        metrics = compute_metrics(self.pairs, consensus, second, consensus)
        self.assertAlmostEqual(metrics["mean_precision_at_3"], 1/3)
        self.assertEqual(metrics["grade_distribution"], {"0": 12, "1": 12, "2": 12})
        self.assertEqual(metrics["fraction_queries_with_relevant_top3"], 1)
        self.assertEqual(metrics["initial_exact_agreement"], 35/36)
        self.assertEqual(metrics["disagreement_pairs"], ["P001"])
        with self.assertRaises(ValueError):
            compute_metrics(self.pairs[:-3], consensus, second, consensus)


if __name__ == "__main__":
    unittest.main()

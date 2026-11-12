"""Technical P4 verification; fixtures are NOT the official P5 query set."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer

from .database import load_database
from .features import load_features, max_sparse_difference, sha256, write_json
from .preprocess import content_tokens
from .search import DEFAULT_DATABASE, ROOT, run, transform_query


def verify(output):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    inputs = output / "inputs"
    inputs.mkdir()
    fixtures = {
        "technical_maritime.txt": "The captain watched the ocean. Sailors repaired the ship and searched for an island in the storm.",
        "technical_self.txt": " ".join((ROOT / "data/corpus/book_0001.txt").read_text(encoding="utf-8-sig").split()[:1000]),
        "empty_vector.txt": "the and a chapter I LX",
        "no_tokens.txt": "123 !!!",
    }
    for name, text in fixtures.items():
        (inputs / name).write_text(text, encoding="utf-8")
    paths = [inputs / name for name in fixtures]
    code = run(paths, output / "batch", trace=True)
    if code != 1:
        raise AssertionError("Expected batch exit 1 due to no_tokens fixture")
    index = load_database(DEFAULT_DATABASE)
    bundle = index.features
    reference = load_features(ROOT / "gd2/artifacts/p2")
    vocabulary = {term: i for i, term in enumerate(bundle.terms)}
    counter = CountVectorizer(vocabulary=vocabulary, tokenizer=content_tokens, token_pattern=None, lowercase=False)
    # Fit the independent transformer on CORPUS counts only, never on queries.
    transformer = TfidfTransformer(sublinear_tf=True, smooth_idf=True, norm="l2").fit(reference.counts)
    checks = []
    for number, (name, text) in enumerate(fixtures.items(), 1):
        folder = output / "batch" / f"Q{number:02}"
        result = json.loads((folder / "results.json").read_text(encoding="utf-8"))
        expected_status = ["ok", "ok", "empty_vector", "error"][number - 1]
        if result["status"] != expected_status:
            raise AssertionError(result)
        if expected_status == "error":
            continue
        expected_q = transformer.transform(counter.transform([text]))
        q, _, _, _ = transform_query(text, vocabulary, bundle.idf)
        error = max_sparse_difference(q, expected_q)
        expected_scores = (reference.tfidf @ expected_q.T).toarray().ravel()
        expected_order = sorted(range(len(bundle.documents)), key=lambda i: (-expected_scores[i], bundle.documents[i]["filename"]))
        with (folder / "all_scores.csv").open(encoding="utf-8", newline="") as stream:
            scores = list(csv.DictReader(stream))
        if len(scores) != 1000 or [row["filename"] for row in scores] != [bundle.documents[i]["filename"] for i in expected_order]:
            raise AssertionError("All-score ranking mismatch")
        score_error = max(abs(float(row["score"]) - expected_scores[i]) for row, i in zip(scores, expected_order))
        if error > 1e-10 or score_error > 1e-10:
            raise AssertionError("Query transform or score mismatch")
        if expected_status == "ok":
            if [row["filename"] for row in result["top3"]] != [bundle.documents[i]["filename"] for i in expected_order[:3]]:
                raise AssertionError("Top-3 mismatch")
            for row in result["top3"]:
                if sha256(folder / row["copy_path"]) != row["raw_sha256"]:
                    raise AssertionError("Returned TXT hash mismatch")
        trace = json.loads((folder / "trace_summary.json").read_text())
        checks.append({"fixture": name, "status": result["status"], "max_query_difference": error,
                       "max_score_difference": score_error, "all_scores_ranked_correctly": True,
                       "contributions": trace["contributions"]})
    report = {"status": "passed", "phase": "P4", "purpose": "technical tests only; not P5/P6 quality evaluation",
              "build_id": index.build_info["build_id"], "database_sha256": sha256(DEFAULT_DATABASE),
              "expected_batch_exit_code": code, "checks": checks,
              "source_sha256": {name: sha256(ROOT / "gd2/src" / name) for name in ["search.py", "verify_search.py", "preprocess.py"]}}
    write_json(output / "verification.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "gd2/artifacts/p4")
    args = parser.parse_args()
    print(json.dumps(verify(args.out), indent=2))


if __name__ == "__main__":
    main()

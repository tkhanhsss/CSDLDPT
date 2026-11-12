"""P2 CLI: rebuild, independently compare GD1, and publish verified artifacts."""
import argparse
import importlib.util
import json
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import nltk
import numpy as np
import scipy
import sklearn
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from .features import (TOLERANCE, build_features, load_features, max_sparse_difference,
                       save_features, sha256, validate_features, vectorizer_parameters,
                       write_csv, write_json)
from .preprocess import CONFIG, CONFIG_DIR, STOPWORDS, raw_tokens, token_trace

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "baselines" / CONFIG["baseline_id"]


def verify_baseline() -> dict:
    result = subprocess.run([sys.executable, str(ROOT / "tools/verify_baseline.py")],
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def load_gd1():
    spec = importlib.util.spec_from_file_location("gd1_reference", ROOT / "gd1/gd1_stats.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_texts(manifest: list[dict], documents: list[dict]):
    for index, entry in enumerate(manifest):
        path = ROOT / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"Corpus changed: {path}")
        text = path.read_text(encoding="utf-8-sig")
        tokens = raw_tokens(text)
        import hashlib
        normalized_hash = hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest()
        if len(tokens) != entry["word_count"] or normalized_hash != entry["normalized_token_sha256"]:
            raise ValueError(f"Word counting/normalization differs from GD1: {path}")
        documents.append({"row_index": index, "doc_id": index + 1, "filename": path.name,
                          "relative_path": entry["path"], "raw_sha256": entry["sha256"],
                          "normalized_sha256": normalized_hash, "word_count": len(tokens)})
        yield text
        if (index + 1) % 100 == 0:
            print(f"GD2: {index + 1}/{len(manifest)} documents", flush=True)


def compare_gd1(bundle, manifest: list[dict], output: Path) -> dict:
    import csv
    original = load_gd1()
    if set(STOPWORDS["stop_all"]) != original.STOP_ALL:
        raise ValueError("Frozen stopwords differ from original GD1")

    def texts():
        for index, entry in enumerate(manifest):
            yield original.read_text(ROOT / entry["path"])[0]
            if (index + 1) % 50 == 0:
                print(f"GD1 independent reference: {index + 1}/{len(manifest)} documents", flush=True)

    # Use the untouched GD1 tokenizer (including its uncached PorterStemmer).
    vectorizer = TfidfVectorizer(**vectorizer_parameters(original.content_tokens))
    reference = vectorizer.fit_transform(texts())
    if not np.array_equal(vectorizer.get_feature_names_out(), bundle.terms):
        raise ValueError("Vocabulary differs from independent GD1 rebuild")
    error = max_sparse_difference(reference, bundle.tfidf)
    idf_error = float(np.max(np.abs(vectorizer.idf_ - bundle.idf)))
    with (ROOT / "gd1/results/doc_top_terms.csv").open(encoding="utf-8-sig", newline="") as stream:
        expected = {row["filename"]: row["top5_tfidf_terms"] for row in csv.DictReader(stream)}
    rows = []
    for i, document in enumerate(bundle.documents):
        row = reference.getrow(i)
        top = bundle.terms[row.indices[np.argsort(-row.data)[:5]]]
        actual = ", ".join(top)
        old = expected[document["filename"]]
        rows.append({"filename": document["filename"], "gd1_top5": old,
                     "rebuilt_top5": actual, "exact_match": actual == old})
    write_csv(output / "top5_comparison.csv", list(rows[0]), rows)
    mismatches = [row for row in rows if not row["exact_match"]]
    result = {"method": "Full TfidfVectorizer.fit_transform using original gd1_stats.content_tokens",
              "documents_compared": len(manifest), "vocabulary_exact_match": True,
              "max_tfidf_difference": error, "max_idf_difference": idf_error,
              "gd1_top5_exact_matches": len(rows) - len(mismatches),
              "gd1_top5_mismatches": mismatches,
              "limitation": "GD1 did not persist its full matrix; historical comparison covers top-5 terms only."}
    if error > TOLERANCE or idf_error > TOLERANCE or mismatches:
        write_json(output / "gd1_comparison_failed.json", result)
        raise ValueError(f"GD1 comparison failed: {result}")
    return result


def run(output: Path) -> dict:
    started = time.perf_counter()
    baseline_before = verify_baseline()
    for name in ("configuration.json", "stopwords.json"):
        if (CONFIG_DIR / name).read_bytes() != (BASELINE / name).read_bytes():
            raise ValueError(f"GD2 configuration differs from baseline: {name}")
    if set(ENGLISH_STOP_WORDS) != set(STOPWORDS["english_stop_words"]):
        raise ValueError("Installed scikit-learn stopwords differ from baseline")
    versions = {"python": platform.python_version(), "numpy": np.__version__,
                "scipy": scipy.__version__, "scikit_learn": sklearn.__version__, "nltk": nltk.__version__}
    mismatches = {name: version for name, version in versions.items()
                  if version != CONFIG["reference_gd1_versions"][name]}
    if mismatches:
        raise ValueError(f"Use the pinned P2 environment; version differences: {mismatches}")
    manifest = json.loads((BASELINE / "corpus_manifest.json").read_text(encoding="utf-8"))["files"]
    manifest = sorted(manifest, key=lambda entry: entry["filename"])
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists; choose a new --out directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish only after all checks pass, never expose an incomplete successful build.
    with tempfile.TemporaryDirectory(prefix=".p2-", dir=output.parent) as staging:
        directory = Path(staging)
        documents = []
        build_started = time.perf_counter()
        bundle = build_features(checked_texts(manifest, documents), documents)
        build_seconds = time.perf_counter() - build_started
        checks = validate_features(bundle, (CONFIG["corpus"]["n_files"], CONFIG["expected_feature_count_from_gd1"]))
        print(json.dumps(checks), flush=True)
        reference_started = time.perf_counter()
        comparison = compare_gd1(bundle, manifest, directory)
        reference_seconds = time.perf_counter() - reference_started
        save_features(bundle, directory)
        restored = load_features(directory)
        validate_features(restored, bundle.tfidf.shape)
        reload_error = max_sparse_difference(bundle.tfidf, restored.tfidf)
        if reload_error != 0 or max_sparse_difference(bundle.counts, restored.counts) != 0:
            raise ValueError("NPZ round-trip is not lossless")
        sample_text = (ROOT / manifest[0]["path"]).read_text(encoding="utf-8-sig")[:500]
        trace = token_trace(sample_text)[:30]
        write_csv(directory / "preprocess_sample.csv", list(trace[0]), trace)
        sample_rows = []
        for name in ("adventur", "detect", "love", "mysteri", "ocean", "ship", "war"):
            matches = np.flatnonzero(bundle.terms == name)
            if len(matches):
                j = int(matches[0])
                sample_rows.append({"term": name, "term_id": j + 1, "df": int(bundle.df[j]),
                                    "idf": float(bundle.idf[j]), "status": "retained"})
            else:
                sample_rows.append({"term": name, "term_id": "", "df": "", "idf": "", "status": "not_in_vocabulary"})
        write_csv(directory / "term_samples.csv", list(sample_rows[0]), sample_rows)
        baseline_after = verify_baseline()
        sources = ["gd2/src/preprocess.py", "gd2/src/features.py", "gd2/src/build_features.py",
                   "gd2/config/configuration.json", "gd2/config/stopwords.json", "gd1/gd1_stats.py",
                   "gd1/results/doc_top_terms.csv",
                   f"baselines/{CONFIG['baseline_id']}/corpus_manifest.json",
                   f"baselines/{CONFIG['baseline_id']}/integrity.json"]
        report = {"status": "passed", "phase": "P2", "baseline_id": CONFIG["baseline_id"],
                  "created_at": datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds"),
                  "timezone": "Asia/Bangkok", "versions": versions, "platform": platform.platform(),
                  "configuration": CONFIG, "baseline_before": baseline_before, "baseline_after": baseline_after,
                  "features": checks, "gd1_comparison": comparison,
                  "round_trip_max_difference": reload_error,
                  "word_count_total": sum(row["word_count"] for row in documents),
                  "mapping": {"documents": "filename ascending; doc_id = row_index + 1",
                              "terms": "term_text ascending; term_id = column_index + 1"},
                  "sample_source": {"filename": manifest[0]["filename"],
                                    "selection": "first 30 normalized tokens within first 500 characters; corpus sample, not Q01"},
                  "timing_seconds": {"gd2_build": build_seconds, "gd1_reference": reference_seconds,
                                     "total_before_report": time.perf_counter() - started},
                  "source_sha256": {path: sha256(ROOT / path) for path in sources},
                  "artifacts": {path.name: {"sha256": sha256(path), "size_bytes": path.stat().st_size}
                                for path in sorted(directory.iterdir()) if path.is_file()}}
        write_json(directory / "verification.json", report)
        directory.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "gd2/artifacts/p2")
    args = parser.parse_args()
    report = run(args.out)
    print(json.dumps({"status": report["status"], "out": str(args.out.resolve()),
                      "features": report["features"], "gd1_comparison": report["gd1_comparison"]}, indent=2))


if __name__ == "__main__":
    main()

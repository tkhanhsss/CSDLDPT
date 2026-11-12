"""P4: fixed-vocabulary TF-IDF search using only the SQLite index."""
import argparse
import hashlib
import json
import math
import sqlite3
import tempfile
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy import sparse

from .database import load_database
from .features import TOLERANCE, sha256, write_csv, write_json
from .preprocess import WORD_RE, content_tokens, normalize_text, raw_tokens, token_trace

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = ROOT / "gd2/database/documents.sqlite"
RESULT_FIELDS = ["rank", "doc_id", "filename", "title", "author_display", "label_code",
                 "score", "zero_score", "relative_path", "copy_path", "raw_sha256"]


def transform_query(text, vocabulary, idf):
    """Count stems, ignore OOV, apply corpus IDF; never fit on query text."""
    tokens = content_tokens(text)
    counts = Counter(tokens)
    columns = sorted(vocabulary[term] for term in counts if term in vocabulary)
    by_column = {vocabulary[term]: count for term, count in counts.items() if term in vocabulary}
    frequencies = np.array([by_column[j] for j in columns], dtype=np.int64)
    weights = (1.0 + np.log(frequencies)) * idf[columns]
    norm = float(np.linalg.norm(weights))
    if norm:
        weights /= norm
    q = sparse.csr_matrix((weights, columns, [0, len(columns)]), shape=(1, len(idf)))
    return q, counts, norm, {"content_token_count": len(tokens), "unique_stems": len(counts),
        "in_vocabulary_types": len(columns), "oov_types": sum(term not in vocabulary for term in counts),
        "oov_tokens": sum(n for term, n in counts.items() if term not in vocabulary), "nnz": q.nnz}


def rank_scores(scores, documents):
    return np.lexsort((np.array([row["filename"] for row in documents]), -scores))


def detailed_token_trace(text):
    # Preserve source offsets even if Unicode lowercase expands a character.
    normalized, offsets = [], []
    for position, character in enumerate(text):
        replacement = normalize_text(character).lower()
        normalized.append(replacement)
        offsets.extend([position] * len(replacement))
    rows = token_trace(text)
    for number, (row, match) in enumerate(zip(rows, WORD_RE.finditer("".join(normalized))), 1):
        start, end = offsets[match.start()], offsets[match.end() - 1] + 1
        row.update(token_index=number, original_token=text[start:end], character_start=start, character_end=end)
    return rows


def export_trace(directory, text, index, q, counts, norm, scores, order, top):
    bundle = index.features
    write_csv(directory / "preprocess.csv", ["token_index", "original_token", "character_start", "character_end",
              "token", "base", "decision", "stem"], detailed_token_trace(text))
    vocabulary = {term: i for i, term in enumerate(bundle.terms)}
    query_weights = dict(zip(q.indices, q.data))
    rows = []
    for term, frequency in counts.items():
        j = vocabulary.get(term)
        tf = 1 + math.log(frequency)
        rows.append({"term": term, "term_id": j + 1 if j is not None else "", "count": frequency,
                     "tf": tf, "df": int(bundle.df[j]) if j is not None else "",
                     "idf": float(bundle.idf[j]) if j is not None else "",
                     "raw_weight": tf * float(bundle.idf[j]) if j is not None else 0.0,
                     "weight": float(query_weights.get(j, 0)), "oov": j is None})
    rows.sort(key=lambda row: (-row["weight"], row["term"]))
    write_csv(directory / "query_terms.csv", ["term", "term_id", "count", "tf", "df", "idf", "raw_weight", "weight", "oov"], rows)
    write_csv(directory / "all_scores.csv", ["rank", "doc_id", "filename", "score"],
              ({"rank": rank, "doc_id": bundle.documents[i]["doc_id"],
                "filename": bundle.documents[i]["filename"], "score": float(scores[i])}
               for rank, i in enumerate(order, 1)))
    summaries = []
    for result, i in zip(top, order[:3]):
        row = bundle.tfidf.getrow(int(i))
        contributions = []
        for j, weight in zip(row.indices, row.data):
            if j in query_weights:
                contributions.append({"term_id": int(j) + 1, "term": str(bundle.terms[j]),
                    "query_weight": float(query_weights[j]), "document_weight": float(weight),
                    "contribution": float(query_weights[j] * weight)})
        contributions.sort(key=lambda row: (-row["contribution"], row["term_id"]))
        total = math.fsum(row["contribution"] for row in contributions)
        if abs(total - result["score"]) > TOLERANCE:
            raise ValueError("Term contributions do not sum to cosine")
        write_csv(directory / f"rank{result['rank']}_contributions.csv",
                  ["term_id", "term", "query_weight", "document_weight", "contribution"], contributions)
        summaries.append({"rank": result["rank"], "filename": result["filename"],
                          "score": result["score"], "sum_contributions": total,
                          "absolute_error": abs(total - result["score"])})
    write_json(directory / "trace_summary.json", {"query_l2_raw": norm, "contributions": summaries,
               "idf_source": "SQLite terms.idf", "tf": "1 + ln(count)", "tolerance": TOLERANCE})


def process_query(path, query_id, index, vocabulary, directory, *, trace=False, corpus_root=ROOT):
    started = time.perf_counter()
    if path.suffix.lower() != ".txt":
        raise ValueError("Input must be a TXT file")
    data = path.read_bytes()
    text = data.decode("utf-8-sig")
    if not text.strip():
        raise ValueError("Query file is empty")
    words = raw_tokens(text)
    if not words:
        raise ValueError("Query contains no word tokens")
    transform_started = time.perf_counter()
    q, counts, norm, stats = transform_query(text, vocabulary, index.features.idf)
    transform_seconds = time.perf_counter() - transform_started
    score_started = time.perf_counter()
    scores = (index.features.tfidf @ q.T).toarray().ravel()
    if not np.all(np.isfinite(scores)):
        raise ValueError("Non-finite cosine score")
    score_seconds = time.perf_counter() - score_started
    rank_started = time.perf_counter()
    order = rank_scores(scores, index.features.documents)
    rank_seconds = time.perf_counter() - rank_started
    top, copies = [], []
    if q.nnz:
        for rank, i in enumerate(order[:3], 1):
            doc = index.features.documents[i]
            source = (corpus_root / doc["relative_path"]).resolve()
            allowed = (corpus_root / "data/corpus").resolve()
            if not source.is_relative_to(allowed) or source.name != doc["filename"]:
                raise ValueError("Corpus path does not match document mapping")
            raw = source.read_bytes()
            if hashlib.sha256(raw).hexdigest() != doc["raw_sha256"]:
                raise ValueError(f"Corpus file changed: {doc['filename']}")
            copy_name = f"rank{rank}_{source.name}"
            copies.append((copy_name, raw))
            top.append({"rank": rank, "doc_id": doc["doc_id"], "filename": doc["filename"],
                        "title": doc["title"], "author_display": doc["author_display"],
                        "label_code": doc["label_code"], "score": float(scores[i]),
                        "zero_score": bool(scores[i] == 0), "relative_path": doc["relative_path"],
                        "copy_path": copy_name, "raw_sha256": doc["raw_sha256"]})
    for name, raw in copies:
        (directory / name).write_bytes(raw)
    if trace:
        export_trace(directory, text, index, q, counts, norm, scores, order, top)
    result = {"query_id": query_id, "query_path": str(path.resolve()),
              "query_sha256": hashlib.sha256(data).hexdigest(), "build_id": index.build_info["build_id"],
              "status": "ok" if q.nnz else "empty_vector", "word_count": len(words),
              "statistics": stats, "query_l2_raw": norm, "top3": top,
              "message": "" if q.nnz else "No query features in the corpus vocabulary; no results returned.",
              "timing_seconds": {"transform": transform_seconds, "score": score_seconds,
                                 "ranking": rank_seconds, "total_before_report": time.perf_counter() - started}}
    write_csv(directory / "results.csv", RESULT_FIELDS, top)
    write_json(directory / "results.json", result)
    return result


def run(queries, output, database=DEFAULT_DATABASE, *, trace=False, corpus_root=ROOT):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    if output.is_relative_to((corpus_root / "data/corpus").resolve()):
        raise ValueError("Output must be outside the corpus")
    if not queries:
        raise ValueError("At least one TXT query is required")
    started = time.perf_counter()
    index = load_database(Path(database))
    load_seconds = time.perf_counter() - started
    vocabulary = {term: i for i, term in enumerate(index.features.terms)}
    output.mkdir(parents=True)
    manifest = []
    for number, query in enumerate(queries, 1):
        path, query_id = Path(query), f"Q{number:02}"
        destination = output / query_id
        try:
            with tempfile.TemporaryDirectory(prefix=".query-", dir=output) as temporary:
                result = process_query(path, query_id, index, vocabulary, Path(temporary), trace=trace, corpus_root=corpus_root)
                Path(temporary).rename(destination)
        except Exception as exc:
            destination.mkdir(exist_ok=True)
            result = {"query_id": query_id, "query_path": str(path.resolve()),
                      "build_id": index.build_info["build_id"], "status": "error", "top3": [],
                      "error_type": type(exc).__name__, "message": str(exc)}
            write_json(destination / "results.json", result)
            write_csv(destination / "results.csv", RESULT_FIELDS, [])
        manifest.append({"query_id": query_id, "query_path": str(path.resolve()), "status": result["status"],
                         "result_path": f"{query_id}/results.json"})
        print(f"{query_id}: {result['status']} | {path}", flush=True)
        for row in result["top3"]:
            print(f"  {row['rank']} | {row['filename']} | {row['title']} | {row['author_display']} | {row['label_code']} | {row['score']:.6f}")
        if result.get("message"):
            print("  " + result["message"])
    exit_code = int(any(row["status"] == "error" for row in manifest))
    write_csv(output / "query_manifest.csv", ["query_id", "query_path", "status", "result_path"], manifest)
    write_json(output / "run_metadata.json", {"build_id": index.build_info["build_id"],
        "created_at": datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds"),
        "database": str(Path(database).resolve()), "trace": trace, "n_queries": len(manifest),
        "load_seconds": load_seconds, "total_seconds": time.perf_counter() - started, "exit_code": exit_code,
        "source_sha256": {"search.py": sha256(Path(__file__)), "preprocess.py": sha256(Path(__file__).with_name("preprocess.py"))}})
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", nargs="+", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    try:
        return run(args.query, args.out, args.database, trace=args.trace)
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        parser.exit(1, f"Search failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())

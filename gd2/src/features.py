"""Build and persist complete sparse features; no query fitting or database yet."""
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer

from .preprocess import CONFIG, content_tokens

TOLERANCE = 1e-10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def vectorizer_parameters(tokenizer=content_tokens) -> dict:
    params = dict(CONFIG["tfidf"])
    params.update(tokenizer=tokenizer, dtype=np.float64,
                  ngram_range=tuple(params["ngram_range"]))
    return params


@dataclass
class FeatureBundle:
    documents: list[dict]
    terms: np.ndarray
    counts: sparse.csr_matrix
    tfidf: sparse.csr_matrix
    df: np.ndarray
    idf: np.ndarray
    l2_raw: np.ndarray


def build_features(texts: Iterable[str], documents: list[dict]) -> FeatureBundle:
    params = vectorizer_parameters()
    tfidf_params = {name: params.pop(name) for name in
                    ("norm", "use_idf", "smooth_idf", "sublinear_tf")}
    params["dtype"] = np.int64
    counter = CountVectorizer(**params)
    counts = counter.fit_transform(texts).tocsr()
    counts.sort_indices()
    transformer = TfidfTransformer(**tfidf_params)
    tfidf = transformer.fit_transform(counts).tocsr()
    tfidf.sort_indices()
    raw = counts.astype(np.float64)
    raw.data = (1.0 + np.log(raw.data)) * transformer.idf_[raw.indices]
    return FeatureBundle(documents, counter.get_feature_names_out(), counts, tfidf,
                         np.asarray(counts.getnnz(axis=0), dtype=np.int64),
                         transformer.idf_.copy(),
                         np.sqrt(np.asarray(raw.multiply(raw).sum(axis=1)).ravel()))


def max_sparse_difference(left, right) -> float:
    if left.shape != right.shape:
        raise ValueError(f"Matrix shape mismatch: {left.shape} != {right.shape}")
    difference = left - right
    return float(np.max(np.abs(difference.data))) if difference.nnz else 0.0


def validate_features(bundle: FeatureBundle, expected_shape=None) -> dict:
    counts, matrix = bundle.counts, bundle.tfidf
    shape = matrix.shape
    if expected_shape is not None and shape != tuple(expected_shape):
        raise ValueError(f"Expected {expected_shape}, got {shape}; investigate before P3")
    if counts.shape != shape or len(bundle.documents) != shape[0] or len(bundle.terms) != shape[1]:
        raise ValueError("Feature dimensions/mappings disagree")
    names = [row["filename"] for row in bundle.documents]
    if names != sorted(set(names)) or list(bundle.terms) != sorted(set(bundle.terms)):
        raise ValueError("Filename/term mappings must be unique and ascending")
    for index, document in enumerate(bundle.documents):
        if int(document["row_index"]) != index or int(document["doc_id"]) != index + 1:
            raise ValueError("doc_id must equal row_index + 1")
    if not (counts.has_canonical_format and matrix.has_canonical_format):
        raise ValueError("Matrices must be canonical CSR")
    if not (np.array_equal(counts.indptr, matrix.indptr) and
            np.array_equal(counts.indices, matrix.indices)):
        raise ValueError("Counts and weights must have identical nonzero coordinates")
    if (counts.dtype.kind not in "iu" or np.any(counts.data <= 0) or
            matrix.dtype != np.float64 or not np.all(np.isfinite(matrix.data)) or
            np.any(matrix.data <= 0)):
        raise ValueError("Invalid counts or weights")
    if bundle.df.shape != (shape[1],) or bundle.idf.shape != (shape[1],):
        raise ValueError("Invalid df/IDF dimensions")
    if bundle.l2_raw.shape != (shape[0],):
        raise ValueError("Invalid raw L2 dimensions")
    df = np.asarray(counts.getnnz(axis=0))
    if not np.array_equal(df, bundle.df):
        raise ValueError("Stored df differs from document frequency")
    if np.any(df < CONFIG["tfidf"]["min_df"]) or np.any(df > shape[0] * CONFIG["tfidf"]["max_df"]):
        raise ValueError("Terms violate min_df/max_df")
    idf = np.log((1.0 + shape[0]) / (1.0 + df)) + 1.0
    np.testing.assert_allclose(bundle.idf, idf, rtol=0, atol=TOLERANCE)
    raw = counts.astype(np.float64)
    raw.data = (1.0 + np.log(raw.data)) * idf[raw.indices]
    l2_raw = np.sqrt(np.asarray(raw.multiply(raw).sum(axis=1)).ravel())
    np.testing.assert_allclose(bundle.l2_raw, l2_raw, rtol=0, atol=TOLERANCE)
    row_ids = np.repeat(np.arange(shape[0]), np.diff(counts.indptr))
    raw.data /= l2_raw[row_ids]
    formula_error = max_sparse_difference(matrix, raw)
    norms = np.sqrt(np.asarray(matrix.multiply(matrix).sum(axis=1)).ravel())
    nonempty = np.diff(matrix.indptr) > 0
    norm_error = float(np.max(np.abs(norms[nonempty] - 1))) if np.any(nonempty) else 0.0
    if formula_error > TOLERANCE or norm_error > TOLERANCE:
        raise ValueError("TF-IDF formula or L2 normalization failed")
    return {"shape": list(shape), "nnz": int(matrix.nnz), "dtype": str(matrix.dtype),
            "zero_rows": int((~nonempty).sum()), "df_min": int(df.min()), "df_max": int(df.max()),
            "idf_min": float(idf.min()), "idf_max": float(idf.max()),
            "l2_norm_min": float(norms[nonempty].min()), "l2_norm_max": float(norms[nonempty].max()),
            "max_l2_error": norm_error, "max_formula_error": formula_error,
            "tolerance": TOLERANCE}


def save_features(bundle: FeatureBundle, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    sparse.save_npz(directory / "counts.npz", bundle.counts)
    sparse.save_npz(directory / "tfidf.npz", bundle.tfidf)
    for name in ("df", "idf", "l2_raw"):
        np.save(directory / f"{name}.npy", getattr(bundle, name), allow_pickle=False)
    write_csv(directory / "documents.csv", list(bundle.documents[0]), bundle.documents)
    write_csv(directory / "terms.csv", ["column_index", "term_id", "term_text", "df", "idf"],
              ({"column_index": i, "term_id": i + 1, "term_text": term,
                "df": int(bundle.df[i]), "idf": float(bundle.idf[i])}
               for i, term in enumerate(bundle.terms)))


def load_features(directory: Path) -> FeatureBundle:
    """Read explicit mappings, without pickle or a fitted Python object."""
    with (directory / "documents.csv").open(encoding="utf-8", newline="") as stream:
        documents = list(csv.DictReader(stream))
    with (directory / "terms.csv").open(encoding="utf-8", newline="") as stream:
        terms = list(csv.DictReader(stream))
    for i, row in enumerate(terms):
        if int(row["column_index"]) != i or int(row["term_id"]) != i + 1:
            raise ValueError("term_id must equal column_index + 1")
    bundle = FeatureBundle(documents, np.array([row["term_text"] for row in terms]),
                           sparse.load_npz(directory / "counts.npz").tocsr(),
                           sparse.load_npz(directory / "tfidf.npz").tocsr(),
                           np.load(directory / "df.npy", allow_pickle=False),
                           np.load(directory / "idf.npy", allow_pickle=False),
                           np.load(directory / "l2_raw.npy", allow_pickle=False))
    if not np.array_equal(bundle.df, [int(row["df"]) for row in terms]):
        raise ValueError("CSV/array df mismatch")
    if not np.array_equal(bundle.idf, [float(row["idf"]) for row in terms]):
        raise ValueError("CSV/array IDF mismatch")
    return bundle

"""SQLite storage and explicit-ID CSR loading. No fitting and no NPZ fallback."""
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import sparse

from .features import FeatureBundle, TOLERANCE, max_sparse_difference, validate_features
from .preprocess import CONFIG

SCHEMA = Path(__file__).resolve().parents[1] / "database/schema.sql"
TABLES = ("build_info", "labels", "documents", "terms", "document_terms")


def feature_contract(config: dict) -> dict:
    """Only behavior-affecting settings; ignore dates, paths and historical notes."""
    return {"word_regex": config["corpus"]["word_count_regex"],
            "preprocessing": {key: value for key, value in config["preprocessing"].items()
                              if key != "stopword_source"},
            "tfidf": config["tfidf"]}


def validate_loaded_index(index) -> None:
    """Cheap in-memory guards; full SQL integrity/formula/P2 audit is separate."""
    bundle = index.features
    names = [row["filename"] for row in bundle.documents]
    if names != sorted(set(names)) or list(bundle.terms) != sorted(set(bundle.terms)):
        raise ValueError("Invalid filename/term mapping")
    codes = {row["label_code"] for row in index.labels}
    if any(row["label_code"] not in codes for row in bundle.documents):
        raise ValueError("Missing label mapping")
    if bundle.tfidf.nnz != index.build_info["nnz"]:
        raise ValueError("Feature count mismatch")
    if (np.any(bundle.counts.data <= 0) or not np.all(np.isfinite(bundle.tfidf.data))
            or np.any(bundle.tfidf.data <= 0) or not np.all(np.isfinite(bundle.idf))
            or np.any(bundle.idf < 1)):
        raise ValueError("Invalid feature values")
    norms_squared = np.asarray(bundle.tfidf.multiply(bundle.tfidf).sum(axis=1)).ravel()
    nonempty = np.diff(bundle.tfidf.indptr) > 0
    if np.any(np.abs(norms_squared[nonempty] - 1) > TOLERANCE):
        raise ValueError("Invalid normalized weights")


def connect(path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    connection = sqlite3.connect(path.resolve().as_uri() + ("?mode=ro" if readonly else "?mode=rwc"), uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        connection.close()
        raise RuntimeError("SQLite foreign key enforcement is unavailable")
    if readonly:
        connection.execute("PRAGMA query_only = ON")
    return connection


def insert_dicts(connection, table: str, rows: list[dict]) -> None:
    if table not in TABLES or not rows:
        raise ValueError("Expected a known table and nonempty rows")
    fields = list(rows[0])
    allowed = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if not set(fields) <= allowed or any(set(row) != set(fields) for row in rows):
        raise ValueError(f"Invalid columns for {table}")
    sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})"
    connection.executemany(sql, (tuple(row[field] for field in fields) for row in rows))


@dataclass
class DatabaseIndex:
    build_info: dict
    labels: list[dict]
    features: FeatureBundle


def read_index(connection, *, require_complete: bool = True) -> DatabaseIndex:
    if connection.execute("PRAGMA user_version").fetchone()[0] != 4:
        raise ValueError("Unsupported database schema version")
    builds = list(connection.execute("SELECT * FROM build_info"))
    if len(builds) != 1:
        raise ValueError("Expected exactly one build_info record")
    info = dict(builds[0])
    if require_complete and info["status"] != "complete":
        raise ValueError("Database build is incomplete")
    if feature_contract(json.loads(info["config_json"])) != feature_contract(CONFIG):
        raise ValueError("Database feature configuration is incompatible")
    documents = [dict(row) for row in connection.execute("SELECT * FROM documents ORDER BY doc_id")]
    terms = list(connection.execute("SELECT * FROM terms ORDER BY term_id"))
    n_docs, n_terms, nnz = info["n_docs"], info["n_terms"], info["nnz"]
    if [row["doc_id"] for row in documents] != list(range(1, n_docs + 1)):
        raise ValueError("Document IDs must be contiguous and match build_info")
    if [row["term_id"] for row in terms] != list(range(1, n_terms + 1)):
        raise ValueError("Term IDs must be contiguous and match build_info")
    for i, row in enumerate(documents):
        row["row_index"] = i
    if connection.execute("SELECT COUNT(*) FROM document_terms").fetchone()[0] != nnz:
        raise ValueError("document_terms count differs from build_info")
    row_indices = np.empty(nnz, dtype=np.int32)
    column_indices = np.empty(nnz, dtype=np.int32)
    counts = np.empty(nnz, dtype=np.int64)
    weights = np.empty(nnz, dtype=np.float64)
    cursor = connection.execute("SELECT doc_id, term_id, term_count, weight FROM document_terms ORDER BY doc_id, term_id")
    offset = 0
    while batch := cursor.fetchmany(50_000):
        end = offset + len(batch)
        row_indices[offset:end] = [row[0] - 1 for row in batch]
        column_indices[offset:end] = [row[1] - 1 for row in batch]
        counts[offset:end] = [row[2] for row in batch]
        weights[offset:end] = [row[3] for row in batch]
        offset = end
    if offset != nnz:
        raise ValueError("Feature row count changed while loading")
    coordinates = (row_indices, column_indices)
    shape = (n_docs, n_terms)
    bundle = FeatureBundle(documents, np.array([row["term_text"] for row in terms]),
                           sparse.csr_matrix((counts, coordinates), shape=shape),
                           sparse.csr_matrix((weights, coordinates), shape=shape),
                           np.array([row["df"] for row in terms], dtype=np.int64),
                           np.array([row["idf"] for row in terms], dtype=np.float64),
                           np.array([row["l2_raw"] for row in documents], dtype=np.float64))
    labels = [dict(row) for row in connection.execute("SELECT * FROM labels ORDER BY label_code")]
    return DatabaseIndex(info, labels, bundle)


def validate_database(connection, *, reference=None, expected_documents=None,
                      expected_labels=None, require_complete=True) -> tuple[DatabaseIndex, dict]:
    actual_tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if actual_tables != set(TABLES):
        raise ValueError(f"Unexpected tables: {actual_tables}")
    integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    if integrity != ["ok"] or list(connection.execute("PRAGMA foreign_key_check")):
        raise ValueError("Database integrity or foreign keys failed")
    if connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise ValueError("Foreign keys are disabled")
    indexes = {row[1] for row in connection.execute("PRAGMA index_list(document_terms)")}
    if "idx_document_terms_term_id" not in indexes:
        raise ValueError("Missing term lookup index")
    index = read_index(connection, require_complete=require_complete)
    bundle = index.features
    checks = validate_features(bundle, (index.build_info["n_docs"], index.build_info["n_terms"]))
    # SQL frequency is checked independently of CSR reconstruction.
    bad_df = connection.execute("""SELECT COUNT(*) FROM terms AS t LEFT JOIN
        (SELECT term_id, COUNT(*) AS n FROM document_terms GROUP BY term_id) AS f
        ON t.term_id = f.term_id WHERE t.df != COALESCE(f.n, 0)""").fetchone()[0]
    if bad_df:
        raise ValueError("SQL document frequency mismatch")
    comparison = None
    if reference is not None:
        if not np.array_equal(bundle.terms, reference.terms):
            raise ValueError("Term mapping differs from P2")
        for actual, expected in zip(bundle.documents, reference.documents):
            if any(str(actual[key]) != str(value) for key, value in expected.items()
                   if key != "normalized_sha256"):
                raise ValueError(f"Document mapping differs from P2: {expected['filename']}")
        count_error = max_sparse_difference(bundle.counts, reference.counts)
        weight_error = max_sparse_difference(bundle.tfidf, reference.tfidf)
        if count_error != 0 or weight_error > TOLERANCE:
            raise ValueError("SQLite matrix differs from P2")
        for name in ("df", "idf", "l2_raw"):
            if not np.array_equal(getattr(bundle, name), getattr(reference, name)):
                raise ValueError(f"SQLite {name} differs from P2")
        comparison = {"max_count_difference": count_error, "max_weight_difference": weight_error,
                      "df_idf_l2_raw_exact": True, "mappings_exact": True}
    if expected_documents is not None:
        actual = [{k: v for k, v in row.items() if k != "row_index"} for row in bundle.documents]
        if actual != expected_documents:
            raise ValueError("Document metadata differs from source tables")
    if expected_labels is not None and index.labels != sorted(expected_labels, key=lambda row: row["label_code"]):
        raise ValueError("Label dictionary differs from GD1")
    return index, {"integrity_check": "ok", "foreign_key_violations": 0, "sql_df_mismatches": bad_df,
                   "table_rows": {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES},
                   "features": checks, "p2_comparison": comparison}


def populate_database(path: Path, bundle: FeatureBundle, documents: list[dict], labels: list[dict], info: dict) -> dict:
    """Populate a new staging file in one transaction; roll back any failed check."""
    if path.exists():
        raise FileExistsError(path)
    validate_features(bundle)
    with closing(connect(path)) as connection:
        try:
            connection.executescript("BEGIN IMMEDIATE;\n" + SCHEMA.read_text(encoding="utf-8"))
            insert_dicts(connection, "build_info", [dict(info, singleton=1, status="building")])
            insert_dicts(connection, "labels", labels)
            insert_dicts(connection, "documents", documents)
            connection.executemany("INSERT INTO terms VALUES (?, ?, ?, ?)",
                                   ((i + 1, str(term), int(bundle.df[i]), float(bundle.idf[i]))
                                    for i, term in enumerate(bundle.terms)))
            def entries():
                for i in range(bundle.counts.shape[0]):
                    for k in range(bundle.counts.indptr[i], bundle.counts.indptr[i + 1]):
                        yield i + 1, int(bundle.counts.indices[k]) + 1, int(bundle.counts.data[k]), float(bundle.tfidf.data[k])
            connection.executemany("INSERT INTO document_terms VALUES (?, ?, ?, ?)", entries())
            _, checks = validate_database(connection, reference=bundle, expected_documents=documents,
                                           expected_labels=labels, require_complete=False)
            connection.execute("UPDATE build_info SET status = 'complete' WHERE singleton = 1")
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
    return checks


def load_database(path: Path) -> DatabaseIndex:
    """P4 entry point: one SQLite load with structural checks, no full audit or refit."""
    with closing(connect(path, readonly=True)) as connection:
        connection.execute("BEGIN")  # consistent read snapshot across all tables
        index = read_index(connection)
        validate_loaded_index(index)
        return index

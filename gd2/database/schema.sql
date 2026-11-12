-- P3 schema v4, one frozen corpus build per SQLite file.
-- The caller enables foreign_keys before opening the transaction.
PRAGMA user_version = 4;

CREATE TABLE build_info (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    build_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('building', 'complete')),
    created_at TEXT NOT NULL,
    n_docs INTEGER NOT NULL CHECK (n_docs > 0),
    n_terms INTEGER NOT NULL CHECK (n_terms > 0),
    nnz INTEGER NOT NULL CHECK (nnz > 0),
    config_json TEXT NOT NULL,
    versions_json TEXT NOT NULL,
    corpus_manifest_sha256 TEXT NOT NULL CHECK (length(corpus_manifest_sha256) = 64),
    preprocess_sha256 TEXT NOT NULL CHECK (length(preprocess_sha256) = 64),
    stopwords_sha256 TEXT NOT NULL CHECK (length(stopwords_sha256) = 64),
    p2_verification_sha256 TEXT NOT NULL CHECK (length(p2_verification_sha256) = 64),
    source_hashes_json TEXT NOT NULL
) STRICT;

CREATE TABLE labels (
    label_code TEXT PRIMARY KEY NOT NULL,
    display_name TEXT NOT NULL CHECK (length(display_name) > 0)
) STRICT;

CREATE TABLE documents (
    doc_id INTEGER PRIMARY KEY CHECK (doc_id > 0),
    filename TEXT NOT NULL UNIQUE,
    relative_path TEXT NOT NULL UNIQUE,
    raw_sha256 TEXT NOT NULL CHECK (length(raw_sha256) = 64),
    word_count INTEGER NOT NULL CHECK (word_count > 0),
    label_code TEXT NOT NULL REFERENCES labels(label_code),
    title TEXT NOT NULL CHECK (length(title) > 0),
    author_display TEXT NOT NULL CHECK (length(author_display) > 0),
    l2_raw REAL NOT NULL CHECK (l2_raw >= 0 AND l2_raw < 1e308)
) STRICT;

CREATE TABLE terms (
    term_id INTEGER PRIMARY KEY CHECK (term_id > 0),
    term_text TEXT NOT NULL UNIQUE CHECK (length(term_text) > 0),
    df INTEGER NOT NULL CHECK (df BETWEEN 3 AND 600),
    idf REAL NOT NULL CHECK (idf >= 1 AND idf < 1e308)
) STRICT;

CREATE TABLE document_terms (
    doc_id INTEGER NOT NULL REFERENCES documents(doc_id),
    term_id INTEGER NOT NULL REFERENCES terms(term_id),
    term_count INTEGER NOT NULL CHECK (term_count > 0),
    weight REAL NOT NULL CHECK (weight > 0 AND weight <= 1.0000000001),
    PRIMARY KEY (doc_id, term_id)
) STRICT, WITHOUT ROWID;

CREATE INDEX idx_document_terms_term_id ON document_terms(term_id);

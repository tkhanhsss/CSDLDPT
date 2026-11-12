"""P3 CLI: import the verified P2 bundle into a new frozen SQLite build."""
import argparse
import ast
import csv
import json
import os
import sqlite3
import tempfile
import time
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .database import SCHEMA, connect, populate_database, validate_database
from .features import load_features, sha256, write_json
from .preprocess import CONFIG
from .verify_features import verify as verify_p2

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_P2 = ROOT / "gd2/artifacts/p2"
DEFAULT_DATABASE = ROOT / "gd2/database/documents.sqlite"


def unique_rows(rows: list[dict], key: str, expected: set[str]) -> dict:
    result = {row[key]: row for row in rows}
    if len(result) != len(rows) or set(result) != expected:
        raise ValueError(f"Duplicate/missing/extra metadata keys: {key}")
    return result


def prepare_metadata(bundle):
    expected = {row["filename"] for row in bundle.documents}
    with (ROOT / "data/metadata/selected_stories.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["new_filename", "title", "author"]:
            raise ValueError("Metadata CSV must contain new_filename, title, author in that order")
        metadata = unique_rows(list(reader), "new_filename", expected)
    labels_by_file = unique_rows([json.loads(line) for line in
        (ROOT / "data/metadata/labels.jsonl").read_text(encoding="utf-8-sig").splitlines() if line.strip()], "filename", expected)
    # Read the literal GD1 display dictionary without executing its statistics program.
    tree = ast.parse((ROOT / "gd1/gd1_stats.py").read_text(encoding="utf-8-sig"))
    display = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "LABEL_EN_MAP" for target in node.targets))
    codes = sorted({row["primary"] for row in labels_by_file.values()})
    labels = [{"label_code": code, "display_name": display[code]} for code in codes]
    if len(labels) != 14:
        raise ValueError("Expected 14 corpus labels")
    documents = []
    for i, feature_row in enumerate(bundle.documents):
        name = feature_row["filename"]
        meta, label = metadata[name], labels_by_file[name]
        for field in ("title", "author"):
            if not meta[field].strip():
                raise ValueError(f"Empty {field}: {name}")
        row = {"doc_id": int(feature_row["doc_id"]), "filename": name,
               "relative_path": feature_row["relative_path"],
               "raw_sha256": feature_row["raw_sha256"],
               "word_count": int(feature_row["word_count"]), "label_code": label["primary"],
               "title": meta["title"], "author_display": meta["author"],
               "l2_raw": float(bundle.l2_raw[i])}
        documents.append(row)
    return documents, labels


def run(output: Path, p2: Path) -> dict:
    started = time.perf_counter()
    output, p2 = output.resolve(), p2.resolve()
    report_path = output.with_suffix(".verification.json")
    if output.exists() or report_path.exists():
        raise FileExistsError("Choose a new --out; database/report already exists")
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise RuntimeError("Schema STRICT requires SQLite >= 3.37")
    print("Verifying P2 artifacts and baseline ...", flush=True)
    p2_checks = verify_p2(p2)
    reference = load_features(p2)
    documents, labels = prepare_metadata(reference)
    p2_report = json.loads((p2 / "verification.json").read_text(encoding="utf-8"))
    sources = ["gd2/src/database.py", "gd2/src/build_database.py", "gd2/src/verify_database.py",
               "gd2/database/schema.sql", "data/metadata/selected_stories.csv", "data/metadata/labels.jsonl",
               "gd1/gd1_stats.py",
               "gd2/config/configuration.json", "gd2/config/stopwords.json", "gd2/src/preprocess.py"]
    hashes = {name: sha256(ROOT / name) for name in sources}
    created_at = datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")
    info = {"build_id": f"gd2-p3-{uuid.uuid4().hex}", "created_at": created_at,
            "n_docs": reference.tfidf.shape[0], "n_terms": reference.tfidf.shape[1], "nnz": reference.tfidf.nnz,
            "config_json": json.dumps(CONFIG, ensure_ascii=False),
            "versions_json": json.dumps({"feature_build": p2_report["versions"], "sqlite": sqlite3.sqlite_version}),
            "corpus_manifest_sha256": sha256(ROOT / f"baselines/{CONFIG['baseline_id']}/corpus_manifest.json"),
            "preprocess_sha256": hashes["gd2/src/preprocess.py"], "stopwords_sha256": hashes["gd2/config/stopwords.json"],
            "p2_verification_sha256": sha256(p2 / "verification.json"), "source_hashes_json": json.dumps(hashes)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".p3-", dir=output.parent) as staging:
        temporary = Path(staging) / output.name
        print(f"Importing {len(documents)} documents, {len(reference.terms)} terms, {reference.tfidf.nnz} weights ...", flush=True)
        write_started = time.perf_counter()
        transaction_checks = populate_database(temporary, reference, documents, labels, info)
        build_seconds = time.perf_counter() - write_started
        print("Transaction committed; reopening SQLite for full verification ...", flush=True)
        load_started = time.perf_counter()
        with closing(connect(temporary, readonly=True)) as connection:
            connection.execute("BEGIN")
            _, checks = validate_database(connection, reference=reference, expected_documents=documents, expected_labels=labels)
            page_count = connection.execute("PRAGMA page_count").fetchone()[0]
            page_size = connection.execute("PRAGMA page_size").fetchone()[0]
            label_counts = {row[0]: row[1] for row in connection.execute(
                "SELECT label_code, COUNT(*) FROM documents GROUP BY label_code ORDER BY label_code")}
        load_seconds = time.perf_counter() - load_started
        if checks != transaction_checks:
            raise ValueError("Committed database differs from transaction checks")
        # Detect source/corpus edits that happened during import.
        verify_p2(p2)
        if sha256(p2 / "verification.json") != info["p2_verification_sha256"]:
            raise ValueError("P2 report changed during import")
        if any(sha256(ROOT / name) != digest for name, digest in hashes.items()):
            raise ValueError("P3 sources changed during import")
        report = {"status": "passed", "phase": "P3", "build_id": info["build_id"], "created_at": created_at,
                  "timezone": "Asia/Bangkok", "database_filename": output.name,
                  "database_sha256": sha256(temporary), "size_bytes": temporary.stat().st_size,
                  "page_count": page_count, "page_size": page_size, "sqlite_version": sqlite3.sqlite_version,
                  "p2_verification_sha256": info["p2_verification_sha256"], "source_sha256": hashes,
                  "p2_checks": p2_checks, "checks": checks, "label_distribution": label_counts,
                  "timing_seconds": {"transaction_insert_and_validate": build_seconds,
                                     "reopen_load_and_validate": load_seconds,
                                     "total_before_report": time.perf_counter() - started}}
        staged_report = Path(staging) / report_path.name
        write_json(staged_report, report)
        # Hard links publish complete files and refuse an existing destination.
        os.link(temporary, output)
        os.link(staged_report, report_path)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--p2", type=Path, default=DEFAULT_P2)
    args = parser.parse_args()
    report = run(args.out, args.p2)
    print(json.dumps({"status": report["status"], "database": str(args.out.resolve()),
                      "size_bytes": report["size_bytes"], "checks": report["checks"],
                      "timing_seconds": report["timing_seconds"]}, indent=2))


if __name__ == "__main__":
    main()

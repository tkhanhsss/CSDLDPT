"""P3 read-only verification: hash, metadata, SQL integrity, and all P2 features."""
import argparse
import json
import time
from contextlib import closing
from pathlib import Path

from .build_database import DEFAULT_DATABASE, DEFAULT_P2, ROOT, prepare_metadata
from .database import connect, validate_database
from .features import load_features, sha256
from .verify_features import verify as verify_p2


def verify(path: Path, p2: Path) -> dict:
    started = time.perf_counter()
    report = json.loads(path.with_suffix(".verification.json").read_text(encoding="utf-8"))
    if report["status"] != "passed" or report["phase"] != "P3":
        raise ValueError("Expected a successful P3 report")
    if sha256(path) != report["database_sha256"] or path.stat().st_size != report["size_bytes"]:
        raise ValueError("Database bytes differ from published build")
    for name, digest in report["source_sha256"].items():
        if sha256(ROOT / name) != digest:
            raise ValueError(f"P3 source changed: {name}")
    verify_p2(p2)
    if sha256(p2 / "verification.json") != report["p2_verification_sha256"]:
        raise ValueError("P2 reference build mismatch")
    reference = load_features(p2)
    documents, labels = prepare_metadata(reference)
    with closing(connect(path, readonly=True)) as connection:
        connection.execute("BEGIN")
        index, checks = validate_database(connection, reference=reference, expected_documents=documents, expected_labels=labels)
    if index.build_info["build_id"] != report["build_id"] or checks != report["checks"]:
        raise ValueError("Database differs from verification report")
    if json.loads(index.build_info["source_hashes_json"]) != report["source_sha256"]:
        raise ValueError("Source provenance mismatch")
    if index.build_info["p2_verification_sha256"] != report["p2_verification_sha256"]:
        raise ValueError("Stored P2 provenance mismatch")
    return {"status": "passed", "build_id": report["build_id"], "size_bytes": report["size_bytes"],
            "checks": checks, "verification_seconds": time.perf_counter() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--p2", type=Path, default=DEFAULT_P2)
    args = parser.parse_args()
    print(json.dumps(verify(args.database, args.p2), indent=2))


if __name__ == "__main__":
    main()

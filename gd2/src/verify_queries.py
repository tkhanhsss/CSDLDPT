"""Read-only validation of the locked P5 query set; never runs retrieval."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from .features import sha256
from .prepare_queries import ROOT, SELECTION, extract, raw_tokens, scan_overlap, body_bounds
from .build_features import verify_baseline


def verify(directory, *, deep=False):
    lock = json.loads((directory / "queries.lock.json").read_text(encoding="utf-8"))
    if lock["status"] != "frozen" or lock["phase"] != "P5":
        raise ValueError("Expected a frozen P5 set")
    for relative, digest in lock["files_sha256"].items():
        if sha256(ROOT / relative) != digest:
            raise ValueError(f"Locked input changed: {relative}")
    verify_baseline()
    with (directory / "query_manifest.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    selection = {r["query_id"]: r for r in json.loads(SELECTION.read_text(encoding="utf-8"))["items"]}
    expected_ids = [f"Q{i:02}" for i in range(1, 13)]
    if [r["query_id"] for r in rows] != expected_ids or len({r["source_id"] for r in rows}) != 12:
        raise ValueError("Expected 12 ordered distinct works")
    if {p.name for p in directory.glob("*.txt")} != {f"{qid}.txt" for qid in expected_ids}:
        raise ValueError("Unexpected/missing query TXT")
    groups = Counter(row["content_group"] for row in rows)
    if len(groups) != 6 or set(groups.values()) != {2}:
        raise ValueError("Expected six groups with two queries each")
    audit = json.loads((directory / "outside_corpus_audit.json").read_text(encoding="utf-8"))
    query_sets, source_sets, counts = {}, {}, []
    for row in rows:
        qid = row["query_id"]
        source = ROOT / row["source_file"]
        text = source.read_bytes().decode("utf-8-sig")
        query = (directory / row["filename"]).read_bytes().decode("utf-8")
        regenerated, start, end, n, _ = extract(text, selection[qid]["start_anchor"])
        if (query != regenerated or start != int(row["start_locator"]) or end != int(row["end_locator"])
                or n != int(row["word_count"]) or not 950 <= n <= 1050
                or sha256(source) != row["source_hash"] or sha256(directory / row["filename"]) != row["query_hash"]):
            raise ValueError(f"Source/extraction mismatch: {qid}")
        if row["verification_status"] != "outside_corpus_reviewed":
            raise ValueError(f"Unreviewed query: {qid}")
        evidence = audit["queries"][qid]
        if any(evidence[key] for key in ["title_matches", "query_12gram_hits", "source_30gram_hits"]):
            raise ValueError(f"Overlap requires a new review: {qid}")
        if not evidence.get("review_note"):
            raise ValueError(f"Missing metadata review: {qid}")
        query_sets[qid] = raw_tokens(query)
        a, b = body_bounds(text)
        source_sets[qid] = raw_tokens(text[a:b])
        counts.append(n)
    if deep:
        hits = scan_overlap(query_sets, source_sets, sorted((ROOT / "data/corpus").glob("book_*.txt")))
        if any(value["query_12gram_hits"] or value["source_30gram_hits"] for value in hits.values()):
            raise ValueError("Deep overlap screen failed")
    return {"status": "passed", "queries": len(rows), "distinct_works": 12, "groups": dict(groups),
            "word_count_min": min(counts), "word_count_max": max(counts), "word_count_total": sum(counts),
            "source_substrings_exact": True, "locked_files_checked": len(lock["files_sha256"]),
            "deep_overlap_screen": deep, "retrieval_run": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "gd2/queries")
    parser.add_argument("--deep", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, deep=args.deep), indent=2))


if __name__ == "__main__":
    main()

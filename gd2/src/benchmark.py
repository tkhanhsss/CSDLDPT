"""P6 reproducible timings; no refitting, no tracing in timed query iterations."""
import argparse
import gc
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import subprocess
import tempfile
import time

import numpy as np

from .database import load_database
from .evaluate import ROOT, QUERIES, DATABASE, now, read_csv, read_json
from .features import sha256, write_csv, write_json
from .preprocess import stem
from .search import transform_query, rank_scores, run
from .verify_queries import verify


def measure_query(path, index, vocabulary):
    start = time.perf_counter()
    text = path.read_bytes().decode("utf-8-sig")
    read = time.perf_counter()
    q, _, _, _ = transform_query(text, vocabulary, index.features.idf)
    transformed = time.perf_counter()
    scores = (index.features.tfidf @ q.T).toarray().ravel()
    scored = time.perf_counter()
    order = rank_scores(scores, index.features.documents)
    end = time.perf_counter()
    return {"read_seconds": read-start, "transform_seconds": transformed-read,
            "score_seconds": scored-transformed, "ranking_seconds": end-scored,
            "total_seconds": end-start}, order[:3], scores


def benchmark(output):
    if output.exists():
        raise FileExistsError(output)
    verify(QUERIES)
    manifest = read_csv(QUERIES / "query_manifest.csv")
    paths = [QUERIES / r["filename"] for r in manifest]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".benchmark-", dir=output.parent) as temporary:
        stage = Path(temporary)
        loads = []
        for repeat in range(1, 6):
            gc.collect()
            start = time.perf_counter()
            index = load_database(DATABASE)
            elapsed = time.perf_counter() - start
            loads.append({"repeat": repeat, "load_seconds": elapsed})
            if repeat != 5:
                del index
        vocabulary = {t: j for j, t in enumerate(index.features.terms)}
        reference = {}
        stem.cache_clear()
        for qid, path in zip([r["query_id"] for r in manifest], paths):
            _, order, scores = measure_query(path, index, vocabulary)
            reference[qid] = (order, scores)
        measurements = []
        for repeat in range(1, 6):
            # Rotate query order; preserve the fixed query set and weights.
            for position in np.roll(np.arange(12), repeat-1):
                qid, path = manifest[position]["query_id"], paths[position]
                times, order, scores = measure_query(path, index, vocabulary)
                if not np.array_equal(order, reference[qid][0]) or not np.array_equal(scores, reference[qid][1]):
                    raise ValueError(f"Non-deterministic ranking: {qid}")
                measurements.append({"query_id": qid, "repeat": repeat, **times})
        fields = list(measurements[0])
        write_csv(stage / "query_timings_raw.csv", fields, measurements)
        write_csv(stage / "database_load_raw.csv", list(loads[0]), loads)
        medians = [{"query_id": r["query_id"], **{key: statistics.median(m[key] for m in measurements if m["query_id"] == r["query_id"])
                    for key in fields[2:]}} for r in manifest]
        write_csv(stage / "query_timings_median.csv", list(medians[0]), medians)
        empty = stage / "empty_vector.txt"
        empty.write_text("the and or is a chapter i ii iii\n", encoding="utf-8")
        run([empty], stage / "empty_vector", trace=True)
        empty_result = read_json(stage / "empty_vector/Q01/results.json")
        if empty_result["status"] != "empty_vector" or empty_result["top3"] or list((stage / "empty_vector/Q01").glob("rank*.txt")):
            raise ValueError("Empty-vector case failed")
        # run() records absolute paths inside the staging directory; relocate only these paths.
        for path in [stage / "empty_vector/Q01/results.json"]:
            data = read_json(path)
            data["query_path"] = str((output / "empty_vector.txt").resolve())
            write_json(path, data)
        rows = read_csv(stage / "empty_vector/query_manifest.csv")
        rows[0]["query_path"] = str((output / "empty_vector.txt").resolve())
        write_csv(stage / "empty_vector/query_manifest.csv", list(rows[0]), rows)
        hardware = {"processor": platform.processor(), "logical_cpus": os.cpu_count(), "ram_bytes": None}
        if os.name == "nt":
            command = "$p=Get-CimInstance Win32_Processor; $c=Get-CimInstance Win32_ComputerSystem; @{cpu=$p.Name; physical_cores=$p.NumberOfCores; logical_cpus=$p.NumberOfLogicalProcessors; ram_bytes=$c.TotalPhysicalMemory} | ConvertTo-Json -Compress"
            result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True)
            hardware = json.loads(result.stdout)
        p2 = read_json(ROOT / "gd2/artifacts/p2/verification.json")
        p3 = read_json(ROOT / "gd2/database/documents.verification.json")
        x = index.features.tfidf
        summary = {"status": "passed", "created_at": now(), "build_id": index.build_info["build_id"],
            "database_sha256": sha256(DATABASE), "p5_lock_sha256": sha256(QUERIES / "queries.lock.json"),
            "hardware": hardware, "operating_system": platform.platform(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "packages": {name: version(name) for name in ["numpy", "scipy", "scikit-learn", "nltk"]},
            "method": {"query_warmups": 1, "measured_repeats_per_query": 5, "database_load_repeats": 5,
                "warm_scope": "Read/decode TXT + transform + XqT + rank all 1000; X and stem cache warm; excludes output copies, trace and interpreter startup",
                "load_scope": "load_database: SQLite read, reconstruct index, lightweight validation; excludes interpreter startup and vocabulary dict; OS cache not flushed, not a cold-disk claim",
                "construction_scope": "Historic measured P2/P3 stages, not rebuilt during P6; see original report scopes"},
            "load_seconds_median": statistics.median(r["load_seconds"] for r in loads),
            "query_total_seconds_median_all_60": statistics.median(r["total_seconds"] for r in measurements),
            "query_total_seconds_min_all_60": min(r["total_seconds"] for r in measurements),
            "query_total_seconds_max_all_60": max(r["total_seconds"] for r in measurements),
            "historic_p2_timing_seconds": p2["timing_seconds"], "historic_p3_timing_seconds": p3["timing_seconds"],
            "size_bytes": {"sqlite": DATABASE.stat().st_size,
                "corpus_txt": sum(p.stat().st_size for p in (ROOT / "data/corpus").glob("*.txt")),
                "query_txt": sum(p.stat().st_size for p in paths),
                "tfidf_csr_arrays": int(x.data.nbytes + x.indices.nbytes + x.indptr.nbytes)},
            "memory_note": "CSR array bytes only, not process peak RAM or full DatabaseIndex",
            "empty_vector": {"status": empty_result["status"], "returned_files": 0, "part_of_official_12": False},
            "deterministic_repeats": True,
            "source_sha256": {name: sha256(ROOT / "gd2/src" / name) for name in ["benchmark.py", "evaluate.py", "search.py", "database.py", "preprocess.py"]}}
        write_json(stage / "performance.json", summary)
        stage.rename(output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "gd2/evaluation/p6/performance")
    args = parser.parse_args()
    print(json.dumps(benchmark(args.out), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

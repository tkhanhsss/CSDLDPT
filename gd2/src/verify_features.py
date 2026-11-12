"""Read-only verification of a published P2 bundle; does not fit on text."""
import argparse
import json
from pathlib import Path

from .build_features import ROOT, verify_baseline
from .features import load_features, sha256, validate_features
from .preprocess import CONFIG


def verify(directory: Path) -> dict:
    report = json.loads((directory / "verification.json").read_text(encoding="utf-8"))
    if report["status"] != "passed" or report["phase"] != "P2":
        raise ValueError("Not a completed P2 build")
    for name, expected in report["artifacts"].items():
        path = directory / name
        if path.stat().st_size != expected["size_bytes"] or sha256(path) != expected["sha256"]:
            raise ValueError(f"Artifact missing or changed: {name}")
    for name, expected in report["source_sha256"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError(f"Build source changed since P2: {name}")
    baseline = verify_baseline()
    bundle = load_features(directory)
    checks = validate_features(bundle, (CONFIG["corpus"]["n_files"], CONFIG["expected_feature_count_from_gd1"]))
    if checks != report["features"]:
        raise ValueError("Stored verification statistics differ from current artifacts")
    return {"status": "passed", "artifact_files_checked": len(report["artifacts"]),
            "baseline_ok": baseline["ok"], "features": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "gd2/artifacts/p2")
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), indent=2))


if __name__ == "__main__":
    main()

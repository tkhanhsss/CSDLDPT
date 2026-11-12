"""P6: verify official retrieval, prepare independent judgments, compute P@3."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import csv
import html
import json
import math
from pathlib import Path
import random
import re
import tempfile

import numpy as np

from .database import load_database
from .features import sha256, write_csv, write_json
from .preprocess import content_tokens
from .verify_queries import verify as verify_queries

ROOT = Path(__file__).resolve().parents[2]
QUERIES = ROOT / "gd2/queries"
DATABASE = ROOT / "gd2/database/documents.sqlite"
FIELDS = ["pair_id", "reviewer", "grade", "query_evidence", "document_evidence", "reason"]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def now():
    return datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")


def validate_run(run, index, manifest):
    """Independent dense query formula, all 12,000 scores, ordering and copies."""
    meta = read_json(run / "run_metadata.json")
    bundle = index.features
    if meta["build_id"] != index.build_info["build_id"] or meta["n_queries"] != 12 or meta["exit_code"]:
        raise ValueError("Official run/build mismatch")
    for name, digest in meta["source_sha256"].items():
        if sha256(ROOT / "gd2/src" / name) != digest:
            raise ValueError(f"Search source changed: {name}")
    if [r["query_id"] for r in read_csv(run / "query_manifest.csv")] != [r["query_id"] for r in manifest]:
        raise ValueError("Run query order differs from frozen manifest")
    all_results, pairs, checks = [], [], []
    for source in manifest:
        qid = source["query_id"]
        directory = run / qid
        result = read_json(directory / "results.json")
        if result["query_id"] != qid or result["build_id"] != meta["build_id"] or result["query_sha256"] != source["query_hash"]:
            raise ValueError(f"Query/build mismatch: {qid}")
        if result["status"] != "ok" or len(result["top3"]) != 3:
            raise ValueError(f"Official query {qid} needs explicit protocol review; cannot drop it")
        counts = Counter(content_tokens((QUERIES / source["filename"]).read_text(encoding="utf-8-sig")))
        q = np.array([(1 + math.log(counts[t])) * bundle.idf[j] if counts[t] else 0.
                      for j, t in enumerate(bundle.terms)])
        q /= np.linalg.norm(q)
        scores = np.asarray(bundle.tfidf @ q).ravel()
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], bundle.documents[i]["filename"]))
        saved = read_csv(directory / "all_scores.csv")
        if len(saved) != len(scores):
            raise ValueError(f"Missing full scores: {qid}")
        errors = []
        for rank, (entry, i) in enumerate(zip(saved, order), 1):
            if (int(entry["rank"]), int(entry["doc_id"]), entry["filename"]) != (rank, bundle.documents[i]["doc_id"], bundle.documents[i]["filename"]):
                raise ValueError(f"Ranking/mapping mismatch: {qid}")
            error = abs(float(entry["score"]) - scores[i])
            if not math.isfinite(error) or error > 1e-10:
                raise ValueError(f"Score mismatch: {qid}")
            errors.append(error)
        contribution_errors = []
        for rank, (row, i) in enumerate(zip(result["top3"], order[:3]), 1):
            doc = bundle.documents[i]
            if row["rank"] != rank or any(row[k] != doc[k] for k in ["doc_id", "filename", "title", "author_display", "label_code", "raw_sha256", "relative_path"]):
                raise ValueError(f"Top-3 metadata mismatch: {qid}")
            if not math.isfinite(row["score"]) or abs(row["score"] - scores[i]) > 1e-10:
                raise ValueError(f"Top-3 score mismatch: {qid}")
            if sha256(directory / row["copy_path"]) != doc["raw_sha256"] or sha256(ROOT / doc["relative_path"]) != doc["raw_sha256"]:
                raise ValueError(f"Copy mismatch: {qid}")
            parts = read_csv(directory / f"rank{rank}_contributions.csv")
            error = abs(math.fsum(float(p["contribution"]) for p in parts) - row["score"])
            if not math.isfinite(error) or error > 1e-10:
                raise ValueError(f"Contribution mismatch: {qid}")
            contribution_errors.append(error)
            pairs.append(dict(query_id=qid, rank=rank, filename=row["filename"], title=row["title"],
                              author=row["author_display"], score=row["score"],
                              query_path=f"gd2/queries/{source['filename']}", document_path=doc["relative_path"]))
        checks.append({"query_id": qid, "scores_checked": len(scores), "copies_checked": 3,
                       "max_score_error": float(max(errors)), "max_contribution_error": max(contribution_errors)})
        all_results.append(result)
    return all_results, pairs, checks


def grading_html(pairs, role):
    """Self-contained local form: scores, ranks, labels and corpus filenames omitted."""
    sections = []
    for number, pair in enumerate(pairs, 1):
        q = (ROOT / pair["query_path"]).read_text(encoding="utf-8-sig")
        d = (ROOT / pair["document_path"]).read_text(encoding="utf-8-sig")
        esc = html.escape
        sections.append(f'''<section data-pair="{pair['pair_id']}"><h2>{number}/36 · {pair['pair_id']} · {pair['query_id']}</h2>
<details><summary>Đọc toàn bộ truy vấn</summary><pre>{esc(q)}</pre></details>
<details><summary>Đọc toàn bộ tài liệu ứng viên</summary><pre>{esc(d)}</pre></details>
<label>Mức liên quan <select class="grade"><option value="">Chưa chấm</option><option value="0">0 — không liên quan đáng kể</option><option value="1">1 — liên quan một phần / bối cảnh chung</option><option value="2">2 — sát chủ đề / tình huống trung tâm</option></select></label>
<label>Trích nguyên văn truy vấn làm bằng chứng<textarea class="query_evidence"></textarea></label>
<label>Trích nguyên văn tài liệu làm bằng chứng<textarea class="document_evidence"></textarea></label>
<label>Lý do đánh giá bằng nội dung<textarea class="reason"></textarea></label></section>''')
    return '''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Phiếu chấm ROLE</title>
<style>body{font:17px/1.5 system-ui;max-width:1050px;margin:30px auto;padding:0 20px;color:#1d2833}section{border-top:2px solid #b8cad8;margin-top:35px;padding-top:12px}pre{white-space:pre-wrap;font:16px/1.65 Georgia;max-height:600px;overflow:auto;padding:20px;background:#f2f5f7}label{display:block;margin:12px 0}textarea{display:block;width:98%;min-height:70px;font:16px system-ui}select,input,button{font:16px system-ui;padding:8px}header{background:#eef6ff;padding:18px}button{cursor:pointer}summary{cursor:pointer;padding:10px}</style>
<h1>Phiếu chấm độc lập — ROLE</h1><header><p>Chấm 36 cặp theo nội dung chính của đoạn truy vấn. Mức 2: sát chủ đề/tình huống trung tâm; mức 1: liên quan một phần hoặc chung bối cảnh; mức 0: không liên quan đáng kể. Trùng tên/từ không đủ. Không xem bảng xếp hạng, điểm hoặc phiếu của người kia trước khi nộp.</p>
<p>Đọc đầy đủ truy vấn và phần cần thiết của tài liệu; bằng chứng phải sao chép nguyên văn (cho phép khác khoảng trắng). Kể cả mức 0 cũng cần đoạn trích và lý do chỉ ra khác biệt. Phiếu không chấm sẵn và không chọn đoạn chứng minh thay người chấm.</p>
<label>Tên người chấm <input id="reviewer" placeholder="Nhập tên thành viên"></label>
<button onclick="saveCSV()">Tải CSV điểm đã nhập</button> <button onclick="document.getElementById('restore').click()">Nạp lại CSV đang chấm</button><input hidden id="restore" type="file" accept=".csv"><p id="status"></p>
<p>Xuất CSV thường xuyên để lưu tiến độ. Dữ liệu chưa xuất sẽ mất khi đóng/tải lại trang. Hai thành viên dùng hai tệp A/B riêng.</p></header>SECTIONS
<button onclick="saveCSV()">Tải CSV điểm đã nhập</button>
<script>
const fields=['pair_id','reviewer','grade','query_evidence','document_evidence','reason'];
const sections=Array.from(document.querySelectorAll('section'));
const quote=x=>'"'+String(x).replaceAll('"','""')+'"';
function saveCSV(){let reviewer=document.getElementById('reviewer').value.trim();if(!reviewer){alert('Nhập tên người chấm trước khi xuất.');return;}
let rows=sections.map(s=>[s.dataset.pair,reviewer,...fields.slice(2).map(f=>s.querySelector('.'+f).value)]);
let csv='\\ufeff'+[fields,...rows].map(r=>r.map(quote).join(',')).join('\\r\\n');
let url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));let a=document.createElement('a');a.href=url;a.download='reviewer_ROLE.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
document.getElementById('status').textContent=rows.filter(r=>r[2]!=='').length+'/36 cặp đã có mức chấm. CSV đã xuất, hãy giữ tệp này.';}
function parseCSV(text){let rows=[],row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){let c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if((c==='\\n'||c==='\\r')&&!quoted){if(c==='\\r'&&text[i+1]==='\\n')i++;row.push(cell);rows.push(row);row=[];cell='';}else cell+=c;}if(quoted)throw Error('CSV chưa đóng dấu nháy');if(cell||row.length){row.push(cell);rows.push(row);}return rows;}
document.getElementById('restore').onchange=async e=>{try{let rows=parseCSV((await e.target.files[0].text()).replace(/^\\uFEFF/,''));if(JSON.stringify(rows.shift())!==JSON.stringify(fields))throw Error('Sai cột CSV');let map=new Map(rows.map(r=>[r[0],r]));if(map.size!==36||rows.length!==36||sections.some(s=>!map.has(s.dataset.pair)))throw Error('Sai danh sách cặp');let names=new Set(rows.map(r=>r[1]));if(names.size!==1)throw Error('Tên người chấm không nhất quán');document.getElementById('reviewer').value=rows[0][1];sections.forEach(s=>fields.slice(2).forEach((f,i)=>s.querySelector('.'+f).value=map.get(s.dataset.pair)[i+2]));document.getElementById('status').textContent='Đã nạp điểm từ CSV.';}catch(err){alert(err.message);}};
</script></html>'''.replace('ROLE', role).replace('SECTIONS', '\n'.join(sections))


def prepare(run, output):
    if output.exists():
        raise FileExistsError(output)
    p5 = verify_queries(QUERIES)
    manifest = read_csv(QUERIES / "query_manifest.csv")
    index = load_database(DATABASE)
    results, pairs, checks = validate_run(run, index, manifest)
    # Stable shuffled IDs contain no rank information; map is only for the coordinator.
    random.Random(20261106).shuffle(pairs)
    for number, pair in enumerate(pairs, 1):
        pair["pair_id"] = f"P{number:03}"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".evaluation-", dir=output.parent) as temp:
        stage = Path(temp)
        write_csv(stage / "pair_map.csv", list(pairs[0]), pairs)
        for role, seed in [("A", 61106), ("B", 61107)]:
            order = pairs.copy()
            random.Random(seed).shuffle(order)
            write_csv(stage / f"reviewer_{role}.csv", FIELDS,
                      [dict.fromkeys(FIELDS, "") | {"pair_id": pair["pair_id"]} for pair in order])
            (stage / f"reviewer_{role}.html").write_text(grading_html(order, role), encoding="utf-8")
        write_csv(stage / "consensus.csv", FIELDS,
                  [dict.fromkeys(FIELDS, "") | {"pair_id": pair["pair_id"]} for pair in pairs])
        summary = []
        for result in results:
            for row in result["top3"]:
                summary.append({"query_id": result["query_id"], "word_count": result["word_count"],
                                "nnz": result["statistics"]["nnz"], **row})
        write_csv(stage / "top3_all.csv", list(summary[0]), summary)
        stats = [{"query_id": r["query_id"], "word_count": r["word_count"], **r["statistics"]} for r in results]
        write_csv(stage / "query_statistics.csv", list(stats[0]), stats)
        q1 = stage / "Q01"
        q1.mkdir()
        for filename, limit in [("preprocess.csv", 15), ("query_terms.csv", 15), ("all_scores.csv", 10)]:
            rows = read_csv(run / "Q01" / filename)[:limit]
            write_csv(q1 / filename, list(rows[0]), rows)
        contributions = []
        for rank in range(1, 4):
            rows = read_csv(run / "Q01" / f"rank{rank}_contributions.csv")
            top = [{"rank": rank, "term": r["term"], "query_weight": r["query_weight"],
                    "document_weight": r["document_weight"], "contribution": r["contribution"]} for r in rows[:10]]
            top.extend([{"rank": rank, "term": "REMAINDER", "query_weight": "", "document_weight": "", "contribution": math.fsum(float(r["contribution"]) for r in rows[10:])},
                        {"rank": rank, "term": "TOTAL", "query_weight": "", "document_weight": "", "contribution": math.fsum(float(r["contribution"]) for r in rows)}])
            contributions.extend(top)
        write_csv(q1 / "contributions_top10_remainder.csv", list(contributions[0]), contributions)
        write_json(stage / "technical_verification.json", {"status": "passed", "created_at": now(),
            "build_id": index.build_info["build_id"], "database_sha256": sha256(DATABASE),
            "p5_check": p5, "queries": checks, "scores_checked": 12000, "copies_checked": 36,
            "reference": "Independent dense query formula using frozen SQLite vocabulary/IDF; sparse X @ dense q",
            "human_judgments": "pending", "mean_precision_at_3": None})
        immutable = [p for p in stage.rglob("*") if p.is_file() and p.name not in ["reviewer_A.csv", "reviewer_B.csv", "consensus.csv"]]
        write_json(stage / "evaluation_manifest.json", {"created_at": now(), "run_directory": str(run.resolve()),
            "build_id": index.build_info["build_id"], "p5_lock_sha256": sha256(QUERIES / "queries.lock.json"),
            "source_sha256": sha256(Path(__file__)), "files_sha256": {p.relative_to(stage).as_posix(): sha256(p) for p in immutable},
            "run_files_sha256": {p.relative_to(run).as_posix(): sha256(p) for p in run.rglob("*") if p.is_file()}})
        stage.rename(output)
    return {"status": "prepared", "pairs": 36, "output": str(output), "human_grading": "pending"}


def normalized_quote(value):
    return re.sub(r"\s+", " ", value).strip()


def validate_judgments(rows, pairs, texts):
    """A partial form is pending, never an implicit zero; invalid entries fail closed."""
    expected = {p["pair_id"] for p in pairs}
    if len(rows) != len(expected) or {r["pair_id"] for r in rows} != expected:
        raise ValueError("Missing/duplicate/foreign judgment pair IDs")
    completed, pending, identities = {}, [], set()
    for row in rows:
        pid = row["pair_id"]
        grade = row["grade"].strip()
        if not grade:
            pending.append(pid)
            continue
        if grade not in {"0", "1", "2"}:
            raise ValueError(f"Invalid grade: {pid}")
        if any(not row[field].strip() for field in FIELDS[1:]):
            raise ValueError(f"Grade without reviewer/evidence/reason: {pid}")
        for field, text in zip(["query_evidence", "document_evidence"], texts[pid]):
            if normalized_quote(row[field]) not in normalized_quote(text):
                raise ValueError(f"Evidence is not a verbatim excerpt: {pid}/{field}")
        identities.add(row["reviewer"].strip().casefold())
        completed[pid] = int(grade)
    if len(identities) > 1:
        raise ValueError("One independent form must belong to one reviewer")
    return completed, pending, identities


def compute_metrics(pairs, first, second, consensus):
    expected = {p["pair_id"] for p in pairs}
    if any(set(grades) != expected for grades in [first, second, consensus]):
        raise ValueError("All three sets must contain every judgment")
    if any(g not in {0, 1, 2} for grades in [first, second, consensus] for g in grades.values()):
        raise ValueError("Grade outside 0, 1, 2")
    grouped = {}
    for pair in pairs:
        grouped.setdefault(pair["query_id"], []).append(pair)
    if set(grouped) != {f"Q{i:02}" for i in range(1, 13)} or any(len(group) != 3 or {int(p["rank"]) for p in group} != {1, 2, 3} for group in grouped.values()):
        raise ValueError("Expected 12 queries with exactly three ranked pairs each")
    per_query = [{"query_id": qid, "relevant_at_3": sum(consensus[p["pair_id"]] == 2 for p in group),
                  "precision_at_3": sum(consensus[p["pair_id"]] == 2 for p in group) / 3} for qid, group in sorted(grouped.items())]
    disagreements = sorted(pid for pid in expected if first[pid] != second[pid])
    return {"status": "complete", "queries": 12, "pairs": 36,
            "mean_precision_at_3": sum(r["precision_at_3"] for r in per_query) / 12,
            "fraction_queries_with_relevant_top3": sum(r["relevant_at_3"] > 0 for r in per_query) / 12,
            "initial_exact_agreement": (36 - len(disagreements)) / 36, "disagreement_pairs": disagreements,
            "grade_distribution": {str(g): sum(v == g for v in consensus.values()) for g in [0, 1, 2]},
            "per_query": per_query}


def grade(evaluation, output):
    if output.exists():
        raise FileExistsError(output)
    verify_queries(QUERIES)
    manifest = read_json(evaluation / "evaluation_manifest.json")
    if sha256(QUERIES / "queries.lock.json") != manifest["p5_lock_sha256"] or sha256(Path(__file__)) != manifest["source_sha256"]:
        raise ValueError("Evaluation code/P5 lock changed")
    for relative, digest in manifest["files_sha256"].items():
        if sha256(evaluation / relative) != digest:
            raise ValueError(f"Evaluation evidence changed: {relative}")
    for relative, digest in manifest["run_files_sha256"].items():
        if sha256(Path(manifest["run_directory"]) / relative) != digest:
            raise ValueError(f"Retrieval evidence changed: {relative}")
    pairs = read_csv(evaluation / "pair_map.csv")
    texts = {p["pair_id"]: ((ROOT / p["query_path"]).read_text(encoding="utf-8-sig"),
                             (ROOT / p["document_path"]).read_text(encoding="utf-8-sig")) for p in pairs}
    inputs = {name: read_csv(evaluation / name) for name in ["reviewer_A.csv", "reviewer_B.csv", "consensus.csv"]}
    validated = {name: validate_judgments(rows, pairs, texts) for name, rows in inputs.items()}
    first, second, agreed = (validated[name] for name in inputs)
    if first[2] and second[2] and first[2] == second[2]:
        raise ValueError("Two distinct independent reviewers are required")
    result = {"status": "awaiting_human_judgments", "mean_precision_at_3": None,
              "completed": {name: len(value[0]) for name, value in validated.items()},
              "missing": {name: value[1] for name, value in validated.items()}}
    if not any(value[1] for value in validated.values()):
        result = compute_metrics(pairs, first[0], second[0], agreed[0])
    result.update(created_at=now(), build_id=manifest["build_id"],
                  judgments_sha256={name: sha256(evaluation / name) for name in inputs})
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".grading-", dir=output.parent) as temp:
        stage = Path(temp)
        for name in inputs:
            (stage / name).write_bytes((evaluation / name).read_bytes())
        comparison = []
        for p in sorted(pairs, key=lambda p: (p["query_id"], int(p["rank"]))):
            pid = p["pair_id"]
            a, b = first[0].get(pid, ""), second[0].get(pid, "")
            comparison.append({"pair_id": pid, "query_id": p["query_id"], "rank": p["rank"],
                               "filename": p["filename"], "grade_A": a, "grade_B": b,
                               "initial_agreement": a == b if a != "" and b != "" else "",
                               "consensus_grade": agreed[0].get(pid, "")})
        write_csv(stage / "comparison.csv", list(comparison[0]), comparison)
        write_json(stage / "metrics.json", result)
        if result["status"] == "complete":
            write_csv(stage / "precision_at_3.csv", list(result["per_query"][0]), result["per_query"])
        stage.rename(output)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--run", type=Path, default=ROOT / "gd2/results/p6_official")
    prep.add_argument("--out", type=Path, default=ROOT / "gd2/evaluation/p6")
    grading = commands.add_parser("grade")
    grading.add_argument("--evaluation", type=Path, default=ROOT / "gd2/evaluation/p6")
    grading.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.run, args.out) if args.command == "prepare" else grade(args.evaluation, args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"Evaluation failed: {exc}\n")


if __name__ == "__main__":
    main()

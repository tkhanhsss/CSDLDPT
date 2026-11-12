"""Apply explicit consensus decisions to the frozen pooled evaluation."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from gd2.src.evaluate import read_csv, validate_judgments
from gd2.src.features import sha256, write_csv, write_json
from experiments.passage_rerank.grade import metrics
from experiments.passage_rerank.run import ROOT, FIELDS


def finalize(run, decisions_path, output):
    run, decisions_path, output = run.resolve(), decisions_path.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if not output.is_relative_to((ROOT / 'experiments').resolve()):
        raise ValueError('Output must be under experiments/')
    manifest = json.loads((run / 'manifest.json').read_text(encoding='utf-8'))
    for section, root in [('protected_files_sha256', ROOT), ('candidate_corpus_sha256', ROOT),
                          ('source_sha256', ROOT), ('files_sha256', run)]:
        for relative, digest in manifest[section].items():
            if sha256(root / relative) != digest:
                raise ValueError(f'Frozen evidence changed: {relative}')
    pairs = read_csv(run / 'coordinator/pair_map.csv')
    pair_map = {p['pair_id']: p for p in pairs}
    if len(pair_map) != len(pairs):
        raise ValueError('Duplicate pairs')
    texts = {p['pair_id']: tuple((ROOT / p[f]).read_text(encoding='utf-8-sig')
                               for f in ['query_path', 'document_path']) for p in pairs}
    inputs = {role: read_csv(run / f'reviewers/reviewer_{role}.csv') for role in 'AB'}
    checked = {role: validate_judgments(rows, pairs, texts) for role, rows in inputs.items()}
    if any(v[1] for v in checked.values()) or checked['A'][2] == checked['B'][2]:
        raise ValueError('Require two complete independent forms')
    hashes = {role: sha256(run / f'reviewers/reviewer_{role}.csv') for role in 'AB'}
    initial = json.loads((run / 'grading_round_1/metrics.json').read_text(encoding='utf-8'))
    if hashes != initial['judgments_sha256']:
        raise ValueError('Reviewer files changed since initial comparison')
    grades = {role: value[0] for role, value in checked.items()}
    indexed = {role: {r['pair_id']: r for r in rows} for role, rows in inputs.items()}
    differences = {pid for pid in pair_map if grades['A'][pid] != grades['B'][pid]}
    decision_document = json.loads(decisions_path.read_text(encoding='utf-8'))
    decisions = {r['pair_id']: r for r in decision_document['decisions']}
    if set(decisions) != differences or len(decisions) != len(decision_document['decisions']):
        raise ValueError('Decisions must cover exactly the unresolved pairs')
    consensus, comparison = [], []
    for pid, pair in sorted(pair_map.items()):
        a, b = grades['A'][pid], grades['B'][pid]
        role, source = 'A', 'initial_agreement'
        if pid in decisions:
            d = decisions[pid]
            if d['query_id'] != pair['query_id'] or (d['grade_A'], d['grade_B']) != (a, b):
                raise ValueError(f'Decision mapping mismatch: {pid}')
            if type(d['grade']) is not int or d['grade'] not in {0, 1, 2} or not d['reason'].strip():
                raise ValueError(f'Invalid decision: {pid}')
            if d['grade'] not in (a, b):
                raise ValueError(f'New grade requires explicit evidence selection: {pid}')
            role = 'A' if d['grade'] == a else 'B'
            row = indexed[role][pid] | {'grade': str(d['grade']), 'reason': d['reason']}
            source = 'user_consensus'
        else:
            row = indexed['A'][pid].copy()
        row['reviewer'] = 'consensus_A_B'
        consensus.append(row)
        comparison.append({**pair, 'grade_A': a, 'grade_B': b,
                           'consensus_grade': int(row['grade']), 'decision_source': source,
                           'evidence_from_reviewer': role, 'reason': row['reason']})
    agreed, pending, _ = validate_judgments(consensus, pairs, texts)
    if pending:
        raise ValueError('Consensus is incomplete')
    final = {method: metrics(pairs, agreed, method) for method in ['baseline', 'passage']}
    for method in final:
        selected = [agreed[p['pair_id']] for p in pairs if p[f'{method}_top3_rank']]
        final[method]['grade_distribution'] = {str(g): selected.count(g) for g in range(3)}
    result = {'status': 'complete', 'created_at': datetime.now(timezone.utc).isoformat(),
              'pairs': len(pairs), 'resolved_disagreements': sorted(differences),
              'initial_agreement_count': len(pairs) - len(differences),
              'initial_exact_agreement': (len(pairs) - len(differences)) / len(pairs),
              'pooled_grade_distribution': dict(sorted(Counter(agreed.values()).items())),
              'consensus_metrics': final,
              'passage_minus_baseline_percentage_points': 100 * (final['passage']['mean_precision_at_3'] - final['baseline']['mean_precision_at_3']),
              'judgments_sha256': hashes, 'decision_sha256': sha256(decisions_path),
              'sources_sha256': {p.relative_to(ROOT).as_posix(): sha256(p)
                                 for p in [Path(__file__), Path(__file__).with_name('grade.py')]},
              'evidence_policy': 'For agreement retain A evidence. For a resolved pair retain evidence of a reviewer whose grade matches the user decision. User reason is preserved verbatim.',
              'scope': 'Exploratory comparison on previously inspected Q01-Q12. Historical P6 metrics are unchanged.'}
    per_query = []
    for a, b in zip(final['baseline']['per_query'], final['passage']['per_query']):
        per_query.append({'query_id': a['query_id'], 'baseline_relevant_at_3': a['relevant_at_3'],
                          'passage_relevant_at_3': b['relevant_at_3'], 'baseline_p_at_3': a['precision_at_3'],
                          'passage_p_at_3': b['precision_at_3'],
                          'delta_p_at_3': b['precision_at_3'] - a['precision_at_3']})
    lines = ['# Kết quả chốt thử nghiệm theo đoạn', '',
             f'Đã chốt {len(pairs)}/{len(pairs)} cặp theo hai phiếu độc lập và bảng thống nhất do người dùng gửi. Đã xử lý toàn bộ {len(differences)} bất đồng.', '',
             '| Chỉ số | Cách hiện tại | Xếp hạng theo đoạn |', '|---|---:|---:|']
    a, b = final['baseline'], final['passage']
    lines.extend([f"| Mean P@3 | {a['mean_precision_at_3']:.2%} | {b['mean_precision_at_3']:.2%} |",
                  f"| Kết quả mức 2 | {a['relevant_slots']}/36 | {b['relevant_slots']}/36 |",
                  f"| Truy vấn có ít nhất một kết quả mức 2 | {a['queries_with_relevant_top3']}/12 | {b['queries_with_relevant_top3']}/12 |", '',
                  'Cấu hình Top-30, đoạn 1.000 từ, bước trượt 500 từ không cải thiện kết quả trên bộ truy vấn này. Mean P@3 giảm 5,56 điểm phần trăm.',
                  'Hai cặp mức 2 là E051 ở Q04 và E038 ở Q11. Cả hai có trong Top-3 cách hiện tại và bị loại khỏi Top-3 sau xếp hạng theo đoạn.',
                  'Giữ thuật toán hiện tại cho hệ thống. Kết quả này chỉ áp dụng cho cấu hình đã thử và bộ Q01–Q12 đã xem trước, không chứng minh mọi cách tìm theo đoạn đều kém hơn.', '',
                  '## Phạm vi điểm chấm', '',
                  'Mốc 11,11% của P6 thuộc đợt chấm trước và giữ nguyên. Mốc 5,56% ở đây là chấm lại cách hiện tại trong pool chung của thử nghiệm. So sánh hai phương pháp bằng cùng bộ consensus mới.',
                  'Hai phiếu đầu thống nhất 48/58 cặp, tương đương 82,76%. Việc chốt bất đồng không làm thay đổi tỷ lệ đồng thuận ban đầu.', '',
                  '## Hồ sơ', '',
                  '`consensus.csv` có đủ 58 mức cuối. `comparison.csv` lưu điểm A/B, mức chốt, nguồn quyết định, nguồn trích dẫn và lý do.',
                  '`consensus_decision.json` giữ nguyên bảng quyết định và lý do người dùng. Các tỷ lệ nội dung ước lượng trong lý do là nhận xét của người chấm, không phải số đo tính lại.',
                  '`precision_at_3.csv` lưu kết quả từng truy vấn. `metrics.json` lưu tổng hợp. `manifest.json` khóa hash đầu ra.',
                  'Phiếu A/B gốc, hồ sơ đối chiếu lần 1, CSDL, kết quả chính thức và báo cáo GD2 giữ nguyên.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.consensus-', dir=output.parent) as temporary:
        stage = Path(temporary)
        write_csv(stage / 'consensus.csv', FIELDS, consensus)
        write_csv(stage / 'comparison.csv', list(comparison[0]), comparison)
        write_csv(stage / 'precision_at_3.csv', list(per_query[0]), per_query)
        (stage / 'consensus_decision.json').write_bytes(decisions_path.read_bytes())
        result['consensus_sha256'] = sha256(stage / 'consensus.csv')
        write_json(stage / 'metrics.json', result)
        (stage / 'KET_QUA.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        write_json(stage / 'manifest.json', {'files_sha256': {p.name: sha256(p) for p in stage.iterdir() if p.is_file()}})
        for role in 'AB':
            if sha256(run / f'reviewers/reviewer_{role}.csv') != hashes[role]:
                raise ValueError('Reviewer input changed during finalization')
        stage.rename(output)
    (run / 'coordinator/consensus.csv').write_bytes((output / 'consensus.csv').read_bytes())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--decisions', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = finalize(args.run, args.decisions, args.out)
    print(json.dumps({k: result[k] for k in ['status', 'pairs', 'pooled_grade_distribution',
                                            'passage_minus_baseline_percentage_points']}, indent=2))

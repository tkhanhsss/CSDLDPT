"""Validate pooled human judgments and compare methods without inventing consensus."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from gd2.src.evaluate import read_csv, validate_judgments
from gd2.src.features import sha256, write_csv, write_json
from experiments.passage_rerank.run import ROOT, FIELDS


def metrics(pairs, grades, method):
    rows = []
    for number in range(1, 13):
        qid = f'Q{number:02}'
        selected = [p for p in pairs if p['query_id'] == qid and p[f'{method}_top3_rank']]
        if len(selected) != 3 or {int(p[f'{method}_top3_rank']) for p in selected} != {1, 2, 3}:
            raise ValueError(f'Invalid Top-3: {method}/{qid}')
        relevant = sum(grades[p['pair_id']] == 2 for p in selected)
        rows.append({'query_id': qid, 'relevant_at_3': relevant, 'precision_at_3': relevant / 3})
    return {'relevant_slots': sum(r['relevant_at_3'] for r in rows),
            'mean_precision_at_3': sum(r['precision_at_3'] for r in rows) / 12,
            'queries_with_relevant_top3': sum(r['relevant_at_3'] > 0 for r in rows),
            'per_query': rows}


def grade(directory, output):
    directory, output = directory.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError('Choose a new grading output directory')
    if not output.is_relative_to((ROOT / 'experiments').resolve()):
        raise ValueError('Output must be under experiments/')
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    for section, root in [('protected_files_sha256', ROOT), ('candidate_corpus_sha256', ROOT),
                          ('source_sha256', ROOT), ('files_sha256', directory)]:
        for relative, digest in manifest[section].items():
            if sha256(root / relative) != digest:
                raise ValueError(f'Frozen evidence changed: {relative}')
    pairs = read_csv(directory / 'coordinator/pair_map.csv')
    if len({(p['query_id'], p['filename']) for p in pairs}) != len(pairs):
        raise ValueError('Duplicate pooled pairs')
    texts = {p['pair_id']: tuple((ROOT / p[field]).read_text(encoding='utf-8-sig')
                               for field in ['query_path', 'document_path']) for p in pairs}
    sources = {role: directory / f'reviewers/reviewer_{role}.csv' for role in 'AB'}
    hashes = {role: sha256(path) for role, path in sources.items()}
    inputs = {role: read_csv(path) for role, path in sources.items()}
    validated = {role: validate_judgments(rows, pairs, texts) for role, rows in inputs.items()}
    if any(value[1] for value in validated.values()):
        raise ValueError('Both reviewers must complete all pairs before comparison')
    if validated['A'][2] == validated['B'][2]:
        raise ValueError('Require two distinct reviewer identities')
    grades = {role: value[0] for role, value in validated.items()}
    indexed = {role: {r['pair_id']: r for r in rows} for role, rows in inputs.items()}
    differences = sorted(pid for pid in texts if grades['A'][pid] != grades['B'][pid])
    draft, comparison = [], []
    for p in pairs:
        pid = p['pair_id']
        agreed = pid not in differences
        draft.append((indexed['A'][pid] | {'reviewer': 'agreement_A_B'}) if agreed
                     else dict.fromkeys(FIELDS, '') | {'pair_id': pid})
        comparison.append({**p, 'grade_A': grades['A'][pid], 'grade_B': grades['B'][pid],
                           'agreement': agreed, 'consensus_grade': grades['A'][pid] if agreed else ''})
    result = {'status': 'awaiting_consensus' if differences else 'complete',
              'created_at': datetime.now(timezone.utc).isoformat(), 'pairs': len(pairs),
              'validated_completed': {role: len(g) for role, g in grades.items()},
              'judgments_sha256': hashes, 'agreement_count': len(pairs) - len(differences),
              'exact_agreement': (len(pairs) - len(differences)) / len(pairs),
              'disagreement_pairs': differences,
              'p_at_3_affecting_disagreements': [pid for pid in differences
                                                if (grades['A'][pid] == 2) != (grades['B'][pid] == 2)],
              'by_reviewer': {role: {m: metrics(pairs, g, m) for m in ['baseline', 'passage']}
                              for role, g in grades.items()},
              'consensus_metrics': None if differences else
                                   {m: metrics(pairs, grades['A'], m) for m in ['baseline', 'passage']},
              'source_sha256': sha256(Path(__file__)),
              'note': 'Regraded baseline uses current pooled judgments. Historical P6 metrics remain separate.'}
    report = ['# Đối chiếu hai phiếu thử nghiệm', '',
              f"Đã kiểm tra đủ {len(pairs)} cặp mỗi phiếu, đúng mã cặp, mức điểm và trích dẫn nguyên văn.",
              f"Hai phiếu thống nhất {result['agreement_count']}/{len(pairs)} cặp ({result['exact_agreement']:.2%}). Có {len(differences)} cặp cần chốt.", '',
              '## Kết quả theo từng người chấm', '',
              '| Người chấm | Cách hiện tại | Xếp hạng theo đoạn |',
              '|---|---|---|']
    for role in 'AB':
        a, b = [result['by_reviewer'][role][m] for m in ['baseline', 'passage']]
        report.append(f"| {role} | {a['mean_precision_at_3']:.2%} ({a['relevant_slots']}/36 mức 2) | {b['mean_precision_at_3']:.2%} ({b['relevant_slots']}/36 mức 2) |")
    report.extend(['', 'Đây là P@3 theo từng phiếu, chưa phải kết quả consensus cuối cùng.',
                   'Cách theo đoạn chưa cho thấy cải thiện trong lượt chấm này. E038 và E051 là hai bất đồng ảnh hưởng P@3, đều thuộc Top-3 cách hiện tại.',
                   'Mốc P6 cũ là 11,11% từ đợt chấm trước. Đợt này chấm lại các cặp trong cùng pool, nên không ghép điểm P6 cũ với điểm mới để so sánh.', '',
                   '## Chốt các cặp bất đồng', '',
                   'Hai người trao đổi dựa trên chủ đề hoặc tình huống chính của truy vấn và bằng chứng trong tài liệu. Mức 2 không đòi hỏi cốt truyện giống hệt. Mức 1 là liên quan một phần hoặc chung bối cảnh. Mức 0 là không liên quan đáng kể.',
                   'Bảng bên dưới ẩn phương pháp và thứ hạng. Đọc phần lý do chi tiết rồi gửi lại mức cuối cho 10 mã cặp.', '',
                   '| Mã cặp | Truy vấn | A | B |', '|---|---|---|---|'])
    pair_lookup = {p['pair_id']: p for p in pairs}
    for pid in differences:
        report.append(f"| {pid} | {pair_lookup[pid]['query_id']} | {grades['A'][pid]} | {grades['B'][pid]} |")
    for pid in differences:
        report.extend(['', f"### {pid} · {pair_lookup[pid]['query_id']}", ''])
        for role in 'AB':
            row = indexed[role][pid]
            report.extend([f"**Người {role}, mức {row['grade']}**", '', row['reason'], '',
                           'Trích truy vấn', '', '> ' + row['query_evidence'].replace('\n', '\n> '), '',
                           'Trích tài liệu', '', '> ' + row['document_evidence'].replace('\n', '\n> '), ''])
    report.extend(['## Tệp kết quả', '',
                   '`consensus_draft.csv` điền 48 cặp hai người đồng ý bằng điểm và bằng chứng của A, ghi người chấm là agreement_A_B. Các cặp bất đồng để trống. Đây là bản tổng hợp, không phải phiếu độc lập thứ ba.',
                   '`comparison.csv` dành cho người tổng hợp, có ánh xạ hai phương pháp. Hai phiếu gốc được sao nguyên byte vào thư mục này. Không sửa các phiếu gốc.',
                   '`metrics.json` lưu kết quả riêng theo từng người chấm. Kết quả consensus còn trống khi chưa chốt bất đồng.'])
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.grade-', dir=output.parent) as temporary:
        stage = Path(temporary)
        for role, source in sources.items():
            (stage / f'reviewer_{role}.csv').write_bytes(source.read_bytes())
            if sha256(stage / f'reviewer_{role}.csv') != hashes[role]:
                raise ValueError('Reviewer file changed during grading')
        write_csv(stage / 'comparison.csv', list(comparison[0]), comparison)
        write_csv(stage / 'consensus_draft.csv', FIELDS, draft)
        write_json(stage / 'metrics.json', result)
        (stage / 'DOI_CHIEU_CHAM.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
        stage.rename(output)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = grade(args.run, args.out)
    print(json.dumps({k: result[k] for k in ['status', 'pairs', 'agreement_count', 'disagreement_pairs',
                                            'p_at_3_affecting_disagreements', 'by_reviewer']}, indent=2))

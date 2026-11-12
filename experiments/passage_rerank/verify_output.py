"""Read-only audit of exported rankings, pooling, reviewer forms and file hashes."""
import argparse
from collections import defaultdict
import html
import json
from pathlib import Path
import re

from gd2.src.evaluate import read_csv, validate_judgments
from gd2.src.features import sha256
from gd2.src.preprocess import raw_tokens
from experiments.passage_rerank.export_forms import form_bytes
from experiments.passage_rerank.run import ROOT, FIELDS


def verify(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    summary = json.loads((directory / 'summary.json').read_text(encoding='utf-8'))
    for key in ['protected_files_sha256', 'candidate_corpus_sha256', 'source_sha256']:
        for relative, digest in manifest[key].items():
            assert sha256(ROOT / relative) == digest, relative
    for relative, digest in manifest['files_sha256'].items():
        assert sha256(directory / relative) == digest, relative
    coord = directory / 'coordinator'
    top = read_csv(coord / 'top3_all.csv')
    candidates = read_csv(coord / 'candidates.csv')
    pool = read_csv(coord / 'pair_map.csv')
    passages = read_csv(coord / 'passage_scores.csv')
    grouped = defaultdict(list)
    for row in passages:
        grouped[(row['query_id'], row['filename'])].append(row)
    for row in candidates:
        scored = grouped[(row['query_id'], row['filename'])]
        best = sorted(scored, key=lambda p: (-float(p['score']), int(p['word_start'])))[0]
        assert float(best['score']) == float(row['passage_score'])
        assert best['passage_index'] == row['passage_index']
        assert len(scored) == int(row['passage_count'])
    keys = {(p['query_id'], p['filename']) for p in pool}
    assert len(keys) == len(pool) == summary['unique_pairs']
    assert keys == {(r['query_id'], r['filename']) for r in top}
    shared = 0
    for qid in [f'Q{i:02}' for i in range(1, 13)]:
        rows = [r for r in candidates if r['query_id'] == qid]
        assert len(rows) == summary['parameters']['candidates']
        assert len({r['filename'] for r in rows}) == len(rows)
        assert sorted(int(r['baseline_rank']) for r in rows) == list(range(1, len(rows) + 1))
        for method, field in [('baseline', 'baseline_rank'), ('passage', 'passage_rank')]:
            ranking = sorted(rows, key=lambda r: int(r[field]))
            if method == 'passage':
                assert ranking == sorted(rows, key=lambda r: (-float(r['passage_score']), r['filename']))
            selected = sorted([r for r in top if r['query_id'] == qid and r['method'] == method], key=lambda r: int(r['rank']))
            assert [r['filename'] for r in selected] == [r['filename'] for r in ranking[:3]]
            assert [int(r['rank']) for r in selected] == [1, 2, 3]
        official = json.loads((ROOT / f'gd2/results/p6_official/{qid}/results.json').read_text(encoding='utf-8'))
        assert [r['filename'] for r in sorted(rows, key=lambda r: int(r['baseline_rank']))[:3]] == [r['filename'] for r in official['top3']]
    pair_lookup = {p['pair_id']: p for p in pool}
    for pair in pool:
        related = [r for r in top if (r['query_id'], r['filename']) == (pair['query_id'], pair['filename'])]
        for method in ['baseline', 'passage']:
            ranks = [r['rank'] for r in related if r['method'] == method]
            assert pair[f'{method}_top3_rank'] == (ranks[0] if ranks else '')
        shared += bool(pair['baseline_top3_rank'] and pair['passage_top3_rank'])
        row = next(r for r in candidates if (r['query_id'], r['filename']) == (pair['query_id'], pair['filename']))
        source = (ROOT / pair['document_path']).read_text(encoding='utf-8-sig')
        excerpt = (coord / f"passages/{pair['query_id']}_{pair['filename']}").read_text(encoding='utf-8')
        assert excerpt == source[int(row['char_start']):int(row['char_end'])]
        assert len(raw_tokens(excerpt)) == int(row['word_end']) - int(row['word_start']) + 1
    assert shared == summary['shared_pairs']
    texts = {pid: tuple((ROOT / p[field]).read_text(encoding='utf-8-sig')
                        for field in ('query_path', 'document_path'))
             for pid, p in pair_lookup.items()}
    for role in ['A', 'B']:
        rows = read_csv(directory / f'reviewers/reviewer_{role}.csv')
        assert all(list(r) == FIELDS for r in rows)
        validate_judgments(rows, pool, texts)
        text = form_bytes(directory, role, manifest).decode('utf-8').replace('\r\n', '\n')
        assert 'book_' not in text and 'baseline_rank' not in text and 'passage_score' not in text
        sections = re.findall(r'<section data-pair="(E\d+)">(.*?)</section>', text, re.S)
        assert len(sections) == len(pool) and {pid for pid, _ in sections} == set(pair_lookup)
        for pair_id, section in sections:
            q, d = re.findall(r'<pre>(.*?)</pre>', section, re.S)
            assert (html.unescape(q), html.unescape(d)) == texts[pair_id]
    return {'status': 'passed', 'unique_pairs': len(pool), 'top3_slots': len(top),
            'candidates': len(candidates), 'passages': len(passages), 'shared_pairs': shared,
            'official_files_unchanged': True, 'forms_and_judgments_validated': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory), indent=2))

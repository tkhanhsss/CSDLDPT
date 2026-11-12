"""Exploratory MaxP reranking. Keeps every official GD2 artifact read-only."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import random
import tempfile
import time

import numpy as np
from scipy import sparse

from gd2.src.database import load_database
from gd2.src.evaluate import read_csv, validate_run
from gd2.src.features import sha256, write_csv, write_json
from gd2.src.preprocess import WORD_RE, content_tokens, normalize_text
from gd2.src.search import rank_scores, transform_query
from gd2.src.verify_queries import verify as verify_queries

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FIELDS = ['pair_id', 'reviewer', 'grade', 'query_evidence', 'document_evidence', 'reason']


def word_spans(text):
    """GD1 raw-word boundaries with offsets into the original decoded text."""
    normalized, offsets = [], []
    for position, character in enumerate(text):
        value = normalize_text(character).lower()
        normalized.append(value)
        offsets.extend([position] * len(value))
    return [(offsets[m.start()], offsets[m.end() - 1] + 1)
            for m in WORD_RE.finditer(''.join(normalized))]


def windows(text, width=1000, stride=500):
    if width < 1 or not 1 <= stride <= width:
        raise ValueError('Require width >= stride >= 1')
    spans = word_spans(text)
    if not spans:
        return []
    last = max(0, len(spans) - width)
    starts = list(range(0, last + 1, stride))
    if starts[-1] != last:
        starts.append(last)
    return [{'word_start': start + 1, 'word_end': min(start + width, len(spans)),
             'char_start': spans[start][0], 'char_end': spans[min(start + width, len(spans)) - 1][1]}
            for start in starts]


def independent_cosine(query, passage, vocabulary, idf):
    """Independent dense formula check for each candidate's winning window."""
    vectors = []
    for text in (query, passage):
        counts = Counter(content_tokens(text))
        vector = np.zeros(len(idf), dtype=np.float64)
        for term, count in counts.items():
            if term in vocabulary:
                column = vocabulary[term]
                vector[column] = (1 + np.log(count)) * idf[column]
        norm = np.linalg.norm(vector)
        vectors.append(vector / norm if norm else vector)
    return float(vectors[0] @ vectors[1])


def form_html(pairs, role):
    sections = []
    for number, pair in enumerate(pairs, 1):
        q = (ROOT / pair['query_path']).read_text(encoding='utf-8-sig')
        d = (ROOT / pair['document_path']).read_text(encoding='utf-8-sig')
        sections.append(f'''<section data-pair="{pair['pair_id']}">
<h2>{number}/{len(pairs)} · {pair['pair_id']} · {pair['query_id']}</h2>
<details><summary>Đọc toàn bộ truy vấn</summary><pre>{html.escape(q)}</pre></details>
<details><summary>Đọc toàn bộ tài liệu ứng viên</summary><pre>{html.escape(d)}</pre></details>
<label>Mức liên quan <select class="grade"><option value="">Chưa chấm</option>
<option value="0">0 — không liên quan đáng kể</option><option value="1">1 — liên quan một phần / bối cảnh chung</option>
<option value="2">2 — sát chủ đề / tình huống trung tâm</option></select></label>
<label>Trích nguyên văn truy vấn<textarea class="query_evidence"></textarea></label>
<label>Trích nguyên văn tài liệu<textarea class="document_evidence"></textarea></label>
<label>Lý do đánh giá<textarea class="reason"></textarea></label></section>''')
    template = (HERE / 'reviewer_template.html').read_text(encoding='utf-8')
    return template.replace('@@ROLE@@', role).replace('@@COUNT@@', str(len(pairs))).replace('@@SECTIONS@@', '\n'.join(sections))


def run(output, width=1000, stride=500, candidates=30):
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f'Use a new output directory: {output}')
    if not output.is_relative_to((ROOT / 'experiments').resolve()):
        raise ValueError('Output must be under experiments/')
    if candidates < 3 or candidates > 1000 or width < 1 or not 1 <= stride <= width:
        raise ValueError('Invalid parameters')
    started = time.perf_counter()
    database = ROOT / 'gd2/database/documents.sqlite'
    protected = [database, *sorted((ROOT / 'gd2/src').glob('*.py')),
                 *sorted((ROOT / 'gd2/config').glob('*')),
                 *sorted((ROOT / 'gd2/queries').glob('*')),
                 *sorted((ROOT / 'gd2/results/p6_official').rglob('*')),
                 *sorted((ROOT / 'gd2/evaluation/p6').rglob('*'))]
    before = {p.relative_to(ROOT).as_posix(): sha256(p) for p in protected if p.is_file()}
    query_check = verify_queries(ROOT / 'gd2/queries')
    load_start = time.perf_counter()
    index = load_database(database)
    load_seconds = time.perf_counter() - load_start
    bundle = index.features
    manifest = read_csv(ROOT / 'gd2/queries/query_manifest.csv')
    official, _, official_checks = validate_run(ROOT / 'gd2/results/p6_official', index, manifest)
    vocabulary = {term: i for i, term in enumerate(bundle.terms)}
    cache, corpus_hashes = {}, {}
    top_rows, candidate_rows, all_passages, pool, comparison, timings = [], [], [], {}, [], []
    max_error = 0.0
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.passage-', dir=output.parent) as temporary:
        stage = Path(temporary)
        (stage / 'coordinator/passages').mkdir(parents=True)
        (stage / 'reviewers').mkdir()
        for result in official:
            qid = result['query_id']
            query_path = ROOT / f'gd2/queries/{qid}.txt'
            query = query_path.read_text(encoding='utf-8-sig')
            tick = time.perf_counter()
            q, _, _, _ = transform_query(query, vocabulary, bundle.idf)
            if not q.nnz:
                raise ValueError(f'{qid}: empty query vector')
            scores = (bundle.tfidf @ q.T).toarray().ravel()
            order = rank_scores(scores, bundle.documents)
            baseline_seconds = time.perf_counter() - tick
            if [bundle.documents[i]['filename'] for i in order[:3]] != [r['filename'] for r in result['top3']]:
                raise ValueError(f'{qid}: official baseline mismatch')
            tick = time.perf_counter()
            rows, uncached = [], 0
            for baseline_rank, i in enumerate(order[:candidates], 1):
                doc = bundle.documents[i]
                filename = doc['filename']
                if filename not in cache:
                    uncached += 1
                    source = (ROOT / doc['relative_path']).resolve()
                    if not source.is_relative_to((ROOT / 'data/corpus').resolve()) or sha256(source) != doc['raw_sha256']:
                        raise ValueError(f'Corpus mismatch: {filename}')
                    corpus_hashes[doc['relative_path']] = doc['raw_sha256']
                    text = source.read_text(encoding='utf-8-sig')
                    spans = windows(text, width, stride)
                    matrix = sparse.vstack([transform_query(text[s['char_start']:s['char_end']], vocabulary, bundle.idf)[0]
                                            for s in spans], format='csr')
                    cache[filename] = text, spans, matrix
                text, spans, matrix = cache[filename]
                pscores = (matrix @ q.T).toarray().ravel()
                best = int(np.argmax(pscores))  # earliest window wins exact ties
                span = spans[best]
                if not np.all(np.isfinite(pscores)) or np.any(pscores < 0) or np.any(pscores > 1 + 1e-10):
                    raise ValueError(f'Invalid passage scores: {qid}/{filename}')
                for position, (s, score) in enumerate(zip(spans, pscores), 1):
                    all_passages.append({'query_id': qid, 'filename': filename, 'passage_index': position,
                                         **s, 'score': float(score)})
                rows.append({'query_id': qid, 'filename': filename, 'title': doc['title'],
                             'author': doc['author_display'], 'baseline_rank': baseline_rank,
                             'baseline_score': float(scores[i]), 'passage_score': float(pscores[best]),
                             'passage_index': best + 1, 'passage_count': len(spans), **span})
            rerank_seconds = time.perf_counter() - tick
            rows.sort(key=lambda r: (-r['passage_score'], r['filename']))
            for rank, row in enumerate(rows, 1):
                row['passage_rank'] = rank
                text = cache[row['filename']][0]
                independent = independent_cosine(query, text[row['char_start']:row['char_end']], vocabulary, bundle.idf)
                max_error = max(max_error, abs(independent - row['passage_score']))
                if abs(independent - row['passage_score']) > 1e-10:
                    raise ValueError('Independent cosine check failed')
            candidate_rows.extend(rows)
            lookup = {r['filename']: r for r in rows}
            baseline_top = [r['filename'] for r in result['top3']]
            passage_top = [r['filename'] for r in rows[:3]]
            for method, selected in [('baseline', baseline_top), ('passage', passage_top)]:
                for rank, filename in enumerate(selected, 1):
                    row = lookup[filename]
                    top_rows.append({'method': method, 'rank': rank, **row})
                    key = (qid, filename)
                    if key not in pool:
                        pool[key] = {'query_id': qid, 'filename': filename, 'title': row['title'],
                                     'query_path': f'gd2/queries/{qid}.txt',
                                     'document_path': f'data/corpus/{filename}',
                                     'baseline_top3_rank': '', 'passage_top3_rank': ''}
                    pool[key][f'{method}_top3_rank'] = rank
            for filename in sorted(set(baseline_top + passage_top)):
                row = lookup[filename]
                text = cache[filename][0]
                (stage / f'coordinator/passages/{qid}_{filename}').write_text(
                    text[row['char_start']:row['char_end']], encoding='utf-8')
            shared = len(set(baseline_top) & set(passage_top))
            comparison.append({'query_id': qid, 'shared_top3': shared, 'new_top3': 3 - shared,
                               'pairs_to_grade': 6 - shared})
            timings.append({'query_id': qid, 'baseline_seconds': baseline_seconds,
                            'rerank_seconds_including_uncached_passages': rerank_seconds,
                            'uncached_documents': uncached})
            print(f'{qid}: shared={shared}, new={3-shared}, pairs={6-shared}', flush=True)
        pairs = [pool[key] for key in sorted(pool)]
        random.Random(20261112).shuffle(pairs)
        for number, pair in enumerate(pairs, 1):
            pair['pair_id'] = f'E{number:03}'
        coordinator = stage / 'coordinator'
        for filename, data in [('top3_all.csv', top_rows), ('candidates.csv', candidate_rows),
                               ('passage_scores.csv', all_passages), ('pair_map.csv', pairs),
                               ('comparison.csv', comparison), ('timings.csv', timings)]:
            write_csv(coordinator / filename, list(data[0]), data)
        for role, seed in [('A', 1211), ('B', 1212)]:
            order = pairs.copy()
            random.Random(seed).shuffle(order)
            write_csv(stage / f'reviewers/reviewer_{role}.csv', FIELDS,
                      [dict.fromkeys(FIELDS, '') | {'pair_id': p['pair_id']} for p in order])
            (stage / f'reviewers/reviewer_{role}.html').write_text(form_html(order, role), encoding='utf-8')
        write_csv(coordinator / 'consensus.csv', FIELDS,
                  [dict.fromkeys(FIELDS, '') | {'pair_id': p['pair_id']} for p in pairs])
        summary = {'created_at': datetime.now(timezone.utc).isoformat(), 'status': 'pending_human_grading',
                   'parameters': {'candidates': candidates, 'width_raw_words': width, 'stride_raw_words': stride,
                                  'tail': 'last full window anchored at last word; deduplicate starts',
                                  'score': 'max passage cosine using frozen corpus vocabulary and IDF',
                                  'document_tie': 'filename ascending', 'passage_tie': 'earliest start'},
                   'queries': len(official), 'ranking_slots': len(top_rows), 'unique_pairs': len(pairs),
                   'shared_pairs': sum(c['shared_top3'] for c in comparison),
                   'new_pairs': sum(c['new_top3'] for c in comparison),
                   'unique_candidate_documents': len(cache), 'passages_scored': len(all_passages),
                   'candidate_winners_checked_independently': len(candidate_rows),
                   'max_cosine_error': max_error, 'build_id': index.build_info['build_id'],
                   'database_load_seconds': load_seconds, 'elapsed_seconds': time.perf_counter() - started,
                   'timing_note': 'One exploratory run, cache reused Q01 to Q12. Not a warm benchmark. Validation and export excluded from query timers.',
                   'mean_precision_at_3': None, 'official_baseline_checks': official_checks,
                   'query_lock_check': query_check}
        write_json(stage / 'summary.json', summary)
        (stage / 'README.md').write_text(f'''# Chấm thử nghiệm theo đoạn

Đã chạy Q01–Q12 và gộp Top-3 của hai phương pháp thành **{len(pairs)} cặp riêng biệt**.
Có {summary['shared_pairs']} cặp cùng xuất hiện và {summary['new_pairs']} cặp mới so với Top-3 chính thức.

## Hai thành viên chấm độc lập

1. Gửi riêng `reviewers/reviewer_A.html` cho người A và `reviewers/reviewer_B.html` cho người B. Mỗi HTML tự chứa đầy đủ văn bản.
2. Mỗi người chấm toàn bộ {len(pairs)} cặp trên phiếu của mình, kể cả các cặp đã gặp ở P6. ID E là của đợt này, không phải ID P cũ.
3. Đọc cả truy vấn và phần cần thiết của tài liệu. Mức 2 sát chủ đề hoặc tình huống trung tâm, mức 1 liên quan một phần hoặc chung bối cảnh, mức 0 không liên quan đáng kể. Chỉ trùng tên hoặc từ không đủ để chọn mức 2.
4. Điền hai trích dẫn nguyên văn và lý do cho mỗi cặp, kể cả mức 0. Phiếu để trống, không dùng lại điểm cũ.
5. Nhập tên và bấm tải CSV thường xuyên. Dùng nút nạp CSV để tiếp tục. Trình duyệt không tự lưu khi đóng trang.
6. Gửi lại hai CSV. Sau đó đối chiếu bất đồng và chốt consensus, rồi tính P@3 cho cả hai phương pháp trên cùng bộ điểm.

Phiếu chỉ hiển thị mã cặp, mã truy vấn và nội dung. Trước khi nộp, không xem thư mục `coordinator`, bảng xếp hạng, điểm cũ hoặc phiếu của người kia.

## Dành cho người tổng hợp sau khi chấm

`coordinator/pair_map.csv` là danh sách các cặp cần chấm và ánh xạ vào Top-3 hai phương pháp.
`top3_all.csv` lưu 72 vị trí xếp hạng. `comparison.csv` đếm phần trùng theo truy vấn.
`candidates.csv` lưu 30 ứng viên mỗi truy vấn. `passage_scores.csv` lưu tất cả điểm đoạn.
`passages/` chứa đoạn tốt nhất cho từng cặp trong pool, dành cho kiểm tra kỹ thuật sau khi chấm.
`consensus.csv` để trống cho kết quả chốt. Tọa độ từ bắt đầu từ 1 và bao gồm hai đầu, tọa độ ký tự bắt đầu từ 0 và không bao gồm cuối.

P@3 của mỗi truy vấn bằng số tài liệu mức 2 trong Top-3 chia 3. Lấy trung bình cả 12 truy vấn, đồng thời đếm số truy vấn có ít nhất một tài liệu mức 2.
Chưa có P@3 mới khi chưa chấm xong. Điểm cosine của hai cách có biểu diễn khác nhau, không dùng việc điểm tăng để kết luận chất lượng tốt hơn.
Q01–Q12 là bộ thử nghiệm đã được xem kết quả. Cần bộ truy vấn mới nếu muốn xác nhận khả năng khái quát sau khi chọn cấu hình.

Thông số là Top-{candidates}, đoạn {width} từ, bước trượt {stride} từ. Giữ nguyên vocabulary, IDF và tiền xử lý GD2.
Kết quả này nằm ngoài kết quả GD2 chính thức. Chỉ xếp hạng lại Top-{candidates}, chưa tìm đoạn trên toàn bộ kho.
Số đo thời gian là một lượt chạy có tái sử dụng cache, không so trực tiếp với benchmark P6.
''', encoding='utf-8')
        if any(sha256(ROOT / p) != digest for p, digest in before.items()):
            raise ValueError('A protected official file changed during the experiment')
        if any(sha256(ROOT / p) != digest for p, digest in corpus_hashes.items()):
            raise ValueError('A candidate corpus file changed during the experiment')
        write_json(stage / 'manifest.json', {'official_files_unchanged': True,
                   'protected_files_sha256': before, 'candidate_corpus_sha256': corpus_hashes,
                   'source_sha256': {p.relative_to(ROOT).as_posix(): sha256(p)
                                     for p in [Path(__file__), HERE / 'reviewer_template.html']},
                   'files_sha256': {p.relative_to(stage).as_posix(): sha256(p) for p in stage.rglob('*')
                                    if p.is_file() and p.name not in ('reviewer_A.csv', 'reviewer_B.csv', 'consensus.csv')}})
        stage.rename(output)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--width', type=int, default=1000)
    parser.add_argument('--stride', type=int, default=500)
    parser.add_argument('--candidates', type=int, default=30)
    args = parser.parse_args()
    result = run(args.out, args.width, args.stride, args.candidates)
    print(json.dumps({k: result[k] for k in ['unique_pairs', 'shared_pairs', 'new_pairs', 'max_cosine_error']}, indent=2))

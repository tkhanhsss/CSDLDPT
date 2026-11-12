"""Read-only verification of the frozen pre-GD2 corpus, assets and snapshots."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    baseline = root/'baselines/pre_gd2_2026-11-04'
    problems = []
    integrity = json.loads((baseline/'integrity.json').read_text(encoding='utf-8'))
    for item in integrity['files']:
        p = baseline/item['path']
        if not p.is_file() or sha256(p) != item['sha256']:
            problems.append(f'Baseline file missing/changed: {item["path"]}')
    if problems:
        print(json.dumps({'ok':False,'problems':problems},ensure_ascii=True,indent=2))
        return 1
    corpus = json.loads((baseline/'corpus_manifest.json').read_text(encoding='utf-8'))['files']
    assets = json.loads((baseline/'asset_manifest.json').read_text(encoding='utf-8'))['files']
    expected = {entry['filename'] for entry in corpus}
    actual = {p.name for p in (root/'data/corpus').glob('*.txt')}
    if actual != expected:
        problems.append({'missing_corpus_files':sorted(expected-actual),'extra_corpus_files':sorted(actual-expected)})
    for entry in corpus + assets:
        p = root/entry['path']
        if not p.is_file() or p.stat().st_size != entry['size_bytes'] or sha256(p) != entry['sha256']:
            problems.append(f'Working file missing/changed: {entry["path"]}')
    rows = list(csv.DictReader((root/'data/metadata/selected_stories.csv').open(encoding='utf-8-sig',newline='')))
    labels = [json.loads(line) for line in (root/'data/metadata/labels.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    if len(rows)!=1000 or {r['new_filename'] for r in rows}!=expected:
        problems.append('Metadata coverage mismatch')
    if len(labels)!=1000 or {r['filename'] for r in labels}!=expected:
        problems.append('Label coverage mismatch')
    print(json.dumps({'ok':not problems,'baseline_id':'pre_gd2_2026-11-04',
                      'corpus_files_checked':len(corpus),'gd1_assets_checked':len(assets),
                      'baseline_files_checked':len(integrity['files']),
                      'metadata_rows':len(rows),'label_rows':len(labels),
                      'tfidf_rebuilt':False,'problems':problems},ensure_ascii=True,indent=2))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())

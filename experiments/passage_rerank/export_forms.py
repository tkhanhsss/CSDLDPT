"""Recreate the original HTML forms from the saved pair map and corpus."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import random

from gd2.src.evaluate import read_csv
from experiments.passage_rerank.run import form_html


def form_bytes(directory, role, manifest):
    relative = f'reviewers/reviewer_{role}.html'
    expected = (manifest.get('regenerable_files_sha256', {}).get(relative)
                or manifest['files_sha256'][relative])
    source = directory / relative
    if source.is_file():
        data = source.read_bytes()
        if sha256(data).hexdigest() == expected:
            return data
        raise ValueError(f'HTML checksum mismatch: {source}')

    pairs = read_csv(directory / 'coordinator/pair_map.csv')
    random.Random({'A': 1211, 'B': 1212}[role]).shuffle(pairs)
    content = form_html(pairs, role)
    for newline in ('\n', '\r\n'):
        data = content.replace('\n', newline).encode('utf-8')
        if sha256(data).hexdigest() == expected:
            return data
    raise ValueError(f'Could not reproduce original HTML for reviewer {role}')


def export(directory, output):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    forms = {role: form_bytes(directory, role, manifest) for role in 'AB'}
    output.mkdir(parents=True, exist_ok=False)
    for role, data in forms.items():
        (output / f'reviewer_{role}.html').write_bytes(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    export(args.directory, args.out)

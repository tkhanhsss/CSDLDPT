"""P5 extraction and corpus-overlap screening; does not import or run search."""
import argparse
import csv
import hashlib
import json
import re
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np

from .features import sha256, write_csv, write_json
from .preprocess import WORD_RE, normalize_text, raw_tokens

ROOT = Path(__file__).resolve().parents[2]
SELECTION = ROOT / "gd2/config/p5_selection.json"


def canonical(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def body_bounds(text):
    start = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    end = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.I)
    if not start or not end or end.start() <= start.end():
        raise ValueError("Missing Gutenberg body markers")
    return start.end(), end.start()


def extract(text, anchor):
    lower, upper = body_bounds(text)
    positions = [m.start() for m in re.finditer(re.escape(anchor), text[lower:upper])]
    if len(positions) != 1:
        raise ValueError(f"Anchor must occur exactly once in body: {anchor}")
    start = lower + positions[0]
    rest = text[start:upper]
    normalized = normalize_text(rest).lower()
    if len(normalized) != len(rest):
        raise ValueError("Case normalization changed character offsets")
    tokens = list(WORD_RE.finditer(normalized))
    if len(tokens) < 950:
        raise ValueError("Insufficient source text after anchor")
    candidates = []
    # Prefer complete paragraphs; use a sentence boundary only if necessary.
    for kind, pattern in [("paragraph", r"\r?\n[ \t]*\r?\n"),
                          ("sentence", r"[.!?][\u201d\u2019\"')\]]*(?=\s|$)")]:
        limit = tokens[1050].start() if len(tokens) > 1050 else len(rest)
        for match in re.finditer(pattern, rest[:limit]):
            end = match.start() if kind == "paragraph" else match.end()
            if end < tokens[949].end():
                continue
            fragment = rest[:end].rstrip()
            n = len(raw_tokens(fragment))
            if 950 <= n <= 1050 and fragment[-1] in '.!?\u201d\u2019\"\')':
                candidates.append((abs(n - 1000), end, len(fragment), n, kind))
        if candidates:
            break
    if not candidates:
        raise ValueError("No complete paragraph/sentence ending within 950-1050 words")
    _, _, length, n, kind = min(candidates)
    end = start + length
    query = text[start:end]
    if any(marker in query.lower() for marker in ("[illustration", "project gutenberg", "*** end of")):
        raise ValueError("Excerpt crosses non-narrative material; select another continuous passage")
    return query, start, end, n, kind


def window_hashes(values, width):
    size = len(values) - width + 1
    if size <= 0:
        return np.empty(0, dtype=np.uint64)
    result = np.zeros(size, dtype=np.uint64)
    for offset in range(width):
        result = result * np.uint64(1_000_003) + values[offset:offset + size]
    return result


def scan_overlap(query_tokens, source_tokens, corpus):
    """All query 12-grams; disjoint 30-token anchors across each source body.

    Hashes only select candidates; every reported hit is confirmed with tokens.
    The source anchor grid catches any exact shared run of >=59 tokens.
    """
    vocabulary = {}

    def encode(tokens):
        return np.fromiter((vocabulary.setdefault(token, len(vocabulary) + 1) for token in tokens), dtype=np.uint64)

    lookups = {12: defaultdict(list), 30: defaultdict(list)}
    for width, token_sets, step in [(12, query_tokens, 1), (30, source_tokens, 30)]:
        for qid, tokens in token_sets.items():
            hashes = window_hashes(encode(tokens), width)
            for offset in range(0, len(hashes), step):
                lookups[width][int(hashes[offset])].append((qid, offset))
    keys = {width: np.array(sorted(lookup), dtype=np.uint64) for width, lookup in lookups.items()}
    hits = {qid: {"query_12gram_hits": [], "source_30gram_hits": []} for qid in query_tokens}
    for number, path in enumerate(corpus, 1):
        tokens = raw_tokens(path.read_text(encoding="utf-8-sig"))
        values = encode(tokens)
        for width, token_sets, field in [(12, query_tokens, "query_12gram_hits"), (30, source_tokens, "source_30gram_hits")]:
            hashes = window_hashes(values, width)
            for offset in np.flatnonzero(np.isin(hashes, keys[width])):
                for qid, ref_offset in lookups[width][int(hashes[offset])]:
                    if tokens[offset:offset + width] == token_sets[qid][ref_offset:ref_offset + width]:
                        hits[qid][field].append({"filename": path.name, "corpus_token_offset": int(offset),
                            "source_token_offset" if width == 30 else "query_token_offset": ref_offset,
                            "tokens": " ".join(tokens[offset:offset + width])})
        if number % 100 == 0:
            print(f"Overlap screen: {number}/{len(corpus)} corpus files", flush=True)
    return hits


def prepare(output):
    if output.exists():
        raise FileExistsError(output)
    items = json.loads(SELECTION.read_text(encoding="utf-8"))["items"]
    if len(items) != 12 or len({item["source_id"] for item in items}) != 12:
        raise ValueError("Expected 12 distinct sources")
    with (ROOT / "data/metadata/selected_stories.csv").open(encoding="utf-8", newline="") as stream:
        metadata = list(csv.DictReader(stream))
    corpus = sorted((ROOT / "data/corpus").glob("book_*.txt"))
    if len(corpus) != 1000:
        raise ValueError("Expected 1000 corpus files")
    output.mkdir(parents=True)
    rows, query_sets, source_sets, review = [], {}, {}, {}
    for item in items:
        qid, source_id = item["query_id"], item["source_id"]
        source = ROOT / f"gd2/sources/pg{source_id}.txt"
        text = source.read_bytes().decode("utf-8-sig")
        query, start, end, n, boundary = extract(text, item["start_anchor"])
        (output / f"{qid}.txt").write_bytes(query.encode("utf-8"))
        lower, upper = body_bounds(text)
        query_sets[qid] = raw_tokens(query)
        source_sets[qid] = raw_tokens(text[lower:upper])
        aliases = [canonical(alias) for alias in item["title_aliases"]]
        title_hits = [row for row in metadata if any(alias in canonical(row["title"]) for alias in aliases)]
        author_hits = [row for row in metadata if any(key in canonical(row["author"]) for key in item["author_keys"])]
        review[qid] = {"title_aliases": item["title_aliases"], "title_matches": title_hits,
                       "same_or_similar_author_rows": author_hits, "source_body_tokens": len(source_sets[qid])}
        rows.append({"query_id": qid, "filename": f"{qid}.txt", "source_title": item["source_title"],
            "source_author": item["source_author"], "content_group": item["content_group"],
            "source_id": source_id, "source_url": f"https://www.gutenberg.org/ebooks/{source_id}",
            "source_text_url": f"https://www.gutenberg.org/cache/epub/{source_id}/pg{source_id}.txt",
            "source_file": source.relative_to(ROOT).as_posix(), "source_hash": sha256(source),
            "chapter_or_section": item["chapter_or_section"], "start_locator": start, "end_locator": end,
            "start_excerpt": query[:120], "end_excerpt": query[-120:], "word_count": n,
            "extraction_rule": f"Unique anchor to nearest {boundary} end to 1000 GD1 words within 950-1050; exact continuous decoded UTF-8 substring; offsets 0-based, end-exclusive, CRLF preserved",
            "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "selection_reason": item["selection_reason"],
            "outside_corpus_evidence": f"outside_corpus_audit.json#{qid}", "verification_status": "pending_review"})
        print(f"{qid}: {n} words; {item['source_title']}", flush=True)
    hits = scan_overlap(query_sets, source_sets, corpus)
    for qid in review:
        review[qid].update(hits[qid])
    write_csv(output / "query_manifest.csv", list(rows[0]), rows)
    write_json(output / "outside_corpus_audit.json", {"method": "Title aliases and author review; exhaustive query 12-grams; source 30-token anchors at step 30; hashes verified against exact tokens.",
        "limitation": "No match is screening evidence, not proof across every translation, paraphrase or unseen edition.",
        "metadata_sha256": sha256(ROOT / "data/metadata/selected_stories.csv"),
        "selection_sha256": sha256(SELECTION), "corpus_files": len(corpus), "queries": review})
    print(json.dumps({qid: {"title_matches": len(value["title_matches"]),
        "query_hits": len(value["query_12gram_hits"]), "source_hits": len(value["source_30gram_hits"])} for qid, value in review.items()}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "gd2/queries")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".p5-", dir=args.out.parent) as staging:
        pending = Path(staging) / "queries"
        prepare(pending)
        pending.rename(args.out)


if __name__ == "__main__":
    main()

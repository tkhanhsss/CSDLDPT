#!/usr/bin/env python3

"""

GD1 - Thong ke dac diem bo du lieu van ban (Muc 1) + so lieu mo ta cho Muc 2.



Cach chay:

    pip install numpy pandas matplotlib scikit-learn scipy nltk

    python gd1_stats.py --data_dir ./data --labels ./labels.csv --out ./gd1_out



File nhan (csv hoac jsonl) can co cot ten file va cot nhan chinh, ten cot nhan dang:

    ten file : filename | file | name | id

    nhan     : primary | label | topic

    tuy chon : confidence | summary | secondary

Ten file co the co hoac khong co duoi .txt.

"""

import argparse
from datetime import datetime

import hashlib

import json

import platform

import re

import sys

from collections import Counter

from pathlib import Path



import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import sklearn

import nltk

import scipy

from scipy.sparse import triu

# Cấu hình font chữ hỗ trợ đầy đủ Tiếng Việt có dấu
plt.rcParams["font.sans-serif"] = ["Segoe UI", "Arial", "DejaVu Sans", "Tahoma", "Helvetica"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False

LABEL_EN_MAP = {
    "romance_social": "Romance & social fiction",
    "mystery_crime": "Mystery & crime",
    "adventure_exploration": "Adventure & exploration",
    "war_military": "War & military",
    "maritime_nautical": "Maritime & nautical",
    "historical_biographical": "Historical & biographical",
    "religion_philosophy": "Religion & philosophy",
    "myth_folklore": "Myth & folklore",
    "fantasy_supernatural": "Fantasy & supernatural",
    "science_fiction_speculative": "Science fiction & speculative",
    "travel_geography": "Travel & geography",
    "nature_animals": "Nature & animals",
    "literary_other": "Literary fiction & other",
    "children_animals": "Children's fiction & animals",
    "__missing__": "Unlabeled",
}

# Gộp bí danh để một chủ đề không bị thống kê thành nhiều nhóm.
LABEL_ALIASES = {"science_fiction": "science_fiction_speculative"}

from sklearn.cluster import KMeans

from sklearn.decomposition import TruncatedSVD

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from sklearn.metrics import (adjusted_rand_score, normalized_mutual_info_score,

                             silhouette_score)

from sklearn.preprocessing import normalize
from nltk.stem import PorterStemmer



WORD_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")

MIN_WORDS = 12000

WORDS_PER_PAGE = 600  # theo de bai: 20 trang ~ 12000 tu

STOP = set(ENGLISH_STOP_WORDS)
PORTER_STEMMER = PorterStemmer()





def _roman(n: int) -> str:

    out = ""

    for v, sym in ((50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):

        while n >= v:

            out += sym

            n -= v

    return out





# Manh viet tat (dau nhay cong lam "didn't" bi tach thanh "didn"), tu "chapter" va so La Ma

# cua tieu de chuong: khong mang noi dung chu de nen bi loai khoi thong ke noi dung.

EXTRA_STOP = {"ll", "ve", "re", "d", "m", "s", "t", "didn", "don", "doesn", "couldn",

              "wouldn", "shouldn", "isn", "wasn", "aren", "weren", "hasn", "haven", "hadn",

              "won", "ain", "em", "tis", "twas", "chapter"} | {_roman(n) for n in range(1, 61)}

STOP_ALL = STOP | EXTRA_STOP





def normalize_text(t: str) -> str:

    """Dua dau nhay cong/modifier ve dau nhay thang de khong tach tu viet tat."""

    return t.replace("’", "'").replace("‘", "'").replace("ʼ", "'")





def content_tokens(text: str):

    """Token noi dung da loc va Porter-stem; "john's" -> "john"."""

    out = []

    for w in WORD_RE.findall(normalize_text(text).lower()):

        base = w.split("'")[0]

        if len(base) > 1 and base not in STOP_ALL:

            out.append(PORTER_STEMMER.stem(base))

    return out



# Cac dau hieu tan du can kiem tra sau khi clean

RESIDUE_PATTERNS = {

    "gutenberg": re.compile(r"project gutenberg", re.I),

    "copyright": re.compile(r"copyright|all rights reserved", re.I),

    "chapter_heading": re.compile(r"^\s*chapter\s+[ivxlcdm\d]+\b", re.I | re.M),

    "star_line": re.compile(r"\*{3,}"),

    "mojibake": re.compile(r"â€|Ã.|\ufffd"),

    "all_caps_line": re.compile(r"^[A-Z0-9 ,.'\-]{25,}$", re.M),

    "url": re.compile(r"https?://|www\."),

}





def read_text(path: Path) -> tuple[str, str]:
    """Đọc văn bản và trả encoding để thống kê/kiểm tra dữ liệu đầu vào."""
    for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace"), "utf-8-replace"





def canonical_label(value):
    """Chuẩn hóa tên nhãn và ánh xạ các bí danh đã biết về một mã chuẩn."""
    if pd.isna(value):
        return pd.NA
    label = re.sub(r"[\s-]+", "_", str(value).strip().lower())
    if not label or label in {"none", "nan", "null", "n_a"}:
        return pd.NA
    return LABEL_ALIASES.get(label, label)


def load_labels(path: Path) -> tuple[pd.DataFrame, dict]:

    if path.suffix.lower() in (".jsonl", ".json"):
        if path.suffix.lower() == ".jsonl":
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines()
                    if line.strip()]
        else:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            rows = payload if isinstance(payload, list) else [payload]
        df = pd.DataFrame(rows)

    else:

        df = pd.read_csv(path, encoding="utf-8-sig")

    cols = {c.lower().strip(): c for c in df.columns}

    fcol = next((cols[k] for k in ("filename", "file", "name", "id") if k in cols), None)

    lcol = next((cols[k] for k in ("primary", "label", "topic") if k in cols), None)

    if fcol is None or lcol is None:

        sys.exit(f"Khong tim thay cot ten file / nhan trong {path}. Cac cot hien co: {list(df.columns)}")

    out = pd.DataFrame(index=df.index)

    for extra in ("confidence", "confidence_level", "secondary", "summary"):

        if extra in cols:

            out[extra] = df[cols[extra]].values

    out["stem"] = df[fcol].map(
        lambda value: (Path(str(value).strip().replace("\\", "/")).stem
                       if not pd.isna(value) and str(value).strip() else pd.NA)
    )
    out["label"] = df[lcol].map(canonical_label)
    duplicate_rows = out[out["stem"].duplicated(keep=False)].copy()
    conflicting_stems = []
    label_by_stem = {}
    for stem, group in out.dropna(subset=["stem"]).groupby("stem"):
        distinct_labels = group["label"].dropna().unique().tolist()
        if len(distinct_labels) > 1:
            conflicting_stems.append(stem)
            label_by_stem[stem] = pd.NA
        elif distinct_labels:
            label_by_stem[stem] = distinct_labels[0]
        else:
            label_by_stem[stem] = pd.NA
    out = out.dropna(subset=["stem"]).drop_duplicates("stem", keep="first").copy()
    out["label"] = out["stem"].map(label_by_stem)
    diagnostics = {
        "input_rows": int(len(df)),
        "rows_without_filename": int((df[fcol].isna() | df[fcol].astype("string").str.strip().eq("")).sum()),
        "duplicate_rows": duplicate_rows,
        "conflicting_stems": conflicting_stems,
    }
    return out, diagnostics





def main():

    ap = argparse.ArgumentParser()

    ap.add_argument("--data_dir", required=True)

    ap.add_argument("--labels", default=None)

    ap.add_argument("--out", default="gd1_out")

    ap.add_argument("--k_min", type=int, default=6)

    ap.add_argument("--k_max", type=int, default=14)

    ap.add_argument("--dup_threshold", type=float, default=0.9)

    ap.add_argument("--min_words", type=int, default=MIN_WORDS)

    ap.add_argument("--words_per_page", type=int, default=WORDS_PER_PAGE)

    args = ap.parse_args()

    if args.min_words <= 0 or args.words_per_page <= 0:
        ap.error("--min_words và --words_per_page phải lớn hơn 0")
    if not 0.0 <= args.dup_threshold <= 1.0:
        ap.error("--dup_threshold phải nằm trong khoảng [0, 1]")
    if args.k_min < 2 or args.k_max < 2:
        ap.error("--k_min và --k_max phải ít nhất bằng 2")
    if args.k_min > args.k_max:
        ap.error("--k_min không được lớn hơn --k_max")



    out = Path(args.out)

    out.mkdir(parents=True, exist_ok=True)

    data_dir = Path(args.data_dir).resolve()
    files = sorted(data_dir.glob("book_*.txt"))
    input_pattern = "book_*.txt"
    if not files:
        files = sorted(data_dir.glob("*.txt"))
        input_pattern = "*.txt"

    if not files:

        sys.exit(f"Khong co file .txt nao trong {args.data_dir}")

    print(f"Doc {len(files)} file ...")



    # ---------- 1. Doc file, dem tu, tan du, trung lap ----------

    texts, rows = [], []

    global_cnt = Counter()

    hashes = {}

    encoding_counts = Counter()

    for p in files:

        t, encoding = read_text(p)

        encoding_counts[encoding] += 1

        toks = WORD_RE.findall(normalize_text(t).lower())

        cnt = Counter(toks)

        global_cnt.update(cnt)

        norm_hash = hashlib.sha256(" ".join(toks).encode("utf-8")).hexdigest()

        hashes.setdefault(norm_hash, []).append(p.name)

        row = {"filename": p.name, "stem": p.stem, "encoding": encoding,
               "n_words": len(toks),

               "n_unique": len(cnt), "n_chars": len(t),

               "n_lines": t.count("\n") + 1,

               "type_token_ratio": len(cnt) / max(len(toks), 1)}

        for name, pat in RESIDUE_PATTERNS.items():

            row[f"res_{name}"] = len(pat.findall(t))

        rows.append(row)

        texts.append(t)

    df = pd.DataFrame(rows)



    # ---------- 2. Thong ke do dai ----------

    s = df["n_words"]

    length_stats = {"n_files": int(len(df)), "total_words": int(s.sum()),

                    "min": int(s.min()), "mean": float(s.mean()), "median": float(s.median()),

                    "max": int(s.max()), "std": float(s.std()),

                    "min_word_threshold": int(args.min_words),
                    "words_per_page_assumption": int(args.words_per_page),
                    "files_below_12000": int((s < args.min_words).sum()),

                    "approx_pages_mean_(600w/page)": float(s.mean() / args.words_per_page),

                    "approx_pages_min": float(s.min() / args.words_per_page),

                    "approx_pages_max": float(s.max() / args.words_per_page)}

    short = df[df["n_words"] < args.min_words][["filename", "n_words"]].sort_values("n_words")

    short.to_csv(out / "files_below_min_length.csv", index=False)



    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.set_xlim(min(args.min_words - 2000, int(s.min()) - 1000), max(56000, int(s.max()) + 1000))
    ax.set_ylim(0, 40)
    ax.hist(s, bins=35, color="#2b5c8f", edgecolor="white", alpha=0.88, zorder=3)
    ax.axvline(args.min_words, color="#dc2626", ls="--", lw=2, zorder=4)

    xticks = sorted(set([args.min_words, 20000, 30000, 40000, 50000]))
    xticklabels = [f"{tick:,}".replace(",", ".") for tick in xticks]
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticklabels)

    for tick, label in zip(ax.get_xticks(), ax.get_xticklabels()):
        if tick == args.min_words:
            label.set_color("#dc2626")
            label.set_fontweight("bold")

    ax.set_title("PHÂN BỐ ĐỘ DÀI 1.000 VĂN BẢN TRONG BỘ DỮ LIỆU", fontsize=12, fontweight="bold", pad=12, color="#0f172a")
    ax.set_xlabel("Số lượng từ mỗi văn bản (Word Count)", fontsize=10.5, labelpad=8)
    ax.set_ylabel("Số lượng văn bản (Documents)", fontsize=10.5, labelpad=8)
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(out / "fig_length_hist.png", dpi=300)
    plt.close()



    # ---------- 3. Tu vung, stop words, stemming ----------

    vocab_raw = len(global_cnt)

    content_cnt = Counter()

    for w, c in global_cnt.items():

        base = w.split("'")[0]

        if len(base) > 1 and base not in STOP_ALL:

            content_cnt[base] += c

    vocab_nostop = len(content_cnt)

    vocab_stem = len({PORTER_STEMMER.stem(w) for w in content_cnt})
    stem_note = "PorterStemmer ap dung cho token truoc khi tao TF-IDF"

    total_tokens = sum(global_cnt.values())

    stop_tokens = sum(c for w, c in global_cnt.items() if w.split("'")[0] in STOP)

    stop_types = sum(1 for w in global_cnt if w.split("'")[0] in STOP)

    removed_tokens = total_tokens - sum(content_cnt.values())

    hapax_count = int(sum(1 for c in global_cnt.values() if c == 1))
    vocab_stats = {"total_tokens": int(total_tokens), "vocab_raw": vocab_raw,

                   "vocab_after_stopwords": vocab_nostop, "vocab_after_stemming": vocab_stem,

                   "stem_note": stem_note,

                   "stopword_types_in_vocab": int(stop_types),

                   "stopword_token_share": stop_tokens / max(total_tokens, 1),

                   "removed_token_share_(stop+fragments+chapter+roman)":

                       removed_tokens / max(total_tokens, 1),

                   "hapax_legomena": hapax_count,
                   "hapax_type_share_pct": 100 * hapax_count / max(vocab_raw, 1)}



    pd.DataFrame(global_cnt.most_common(50), columns=["word", "count"]).to_csv(

        out / "top_words_raw.csv", index=False)

    pd.DataFrame(content_cnt.most_common(50), columns=["word", "count"]).to_csv(

        out / "top_words_no_stopwords.csv", index=False)



    ranks = np.arange(1, vocab_raw + 1)
    freqs = np.array(sorted(global_cnt.values(), reverse=True))
    ideal = freqs[0] / ranks

    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.loglog(ranks, freqs, color="#b02a30", lw=2, label="Dữ liệu thực nghiệm (Kho 1.000 tác phẩm)")
    ax.loglog(ranks, ideal, color="#595959", ls="--", lw=1.5, alpha=0.8, label="Đường tham chiếu: f(1)/r")
    zipf_info = chr(10).join([
        f"Tổng lượt từ: {total_tokens:,} tokens",
        f"Từ vựng gốc: {vocab_raw:,} types",
        f"Sau lọc từ dừng: {vocab_nostop:,} types",
        f"Sau Stemming: {vocab_stem:,} stems",
        f"Hapax legomena: {vocab_stats['hapax_legomena']:,} ({vocab_stats['hapax_type_share_pct']:.1f}%)"
    ])
    ax.text(0.96, 0.82, zipf_info, transform=ax.transAxes, fontsize=9.5,
            verticalalignment="top", horizontalalignment="right",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#d1d5db", alpha=0.9))
    ax.set_title("PHÂN BỐ TẦN SUẤT TỪ VÀ ĐƯỜNG THAM CHIẾU ZIPF", fontsize=12, fontweight="bold", pad=12, color="#1a202c")
    ax.set_xlabel("Thứ hạng từ vựng - Rank r (Log scale)", fontsize=10.5, labelpad=8)
    ax.set_ylabel("Tần suất xuất hiện - Frequency f (Log scale)", fontsize=10.5, labelpad=8)
    ax.grid(True, which="both", linestyle=":", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower left", frameon=True, facecolor="white", edgecolor="#ced4da", fontsize=9.5)
    plt.tight_layout()
    plt.savefig(out / "fig_zipf.png", dpi=300)
    plt.close()



    # ---------- 4. TF-IDF de mo ta noi dung ----------

    print("Tinh TF-IDF ...")

    vec = TfidfVectorizer(tokenizer=content_tokens, token_pattern=None, lowercase=False,

                          min_df=3, max_df=0.6, sublinear_tf=True,
                          use_idf=True, smooth_idf=True, norm="l2")

    try:
        X = vec.fit_transform(texts)
    except ValueError as exc:
        sys.exit(f"Khong tao duoc TF-IDF. Kiem tra noi dung/token/stopword: {exc}")

    if X.shape[1] < 2:
        sys.exit("Tu vung TF-IDF co it hon 2 term; khong the chay SVD 2D/KMeans.")

    terms = np.array(vec.get_feature_names_out())



    # top tu TF-IDF cua tung van ban

    top_rows = []

    for i in range(X.shape[0]):

        r = X.getrow(i)

        if r.nnz == 0:

            top_rows.append((df.loc[i, "filename"], ""))

            continue

        idx = r.indices[np.argsort(-r.data)[:5]]

        top_rows.append((df.loc[i, "filename"], ", ".join(terms[idx])))

    pd.DataFrame(top_rows, columns=["filename", "top5_tfidf_terms"]).to_csv(

        out / "doc_top_terms.csv", index=False)



    # ---------- 5. Van ban trung / gan trung ----------

    exact = [v for v in hashes.values() if len(v) > 1]

    similarities = (X @ X.T).tocsr()
    similarities.setdiag(0)
    similarities.eliminate_zeros()
    upper = triu(similarities, k=1, format="coo")
    keep = upper.data > args.dup_threshold
    ii, jj, scores = upper.row[keep], upper.col[keep], upper.data[keep]
    near = pd.DataFrame({"file_a": df.loc[ii, "filename"].values,
                         "file_b": df.loc[jj, "filename"].values,
                         "cosine": scores}).sort_values("cosine", ascending=False)

    near.to_csv(out / "near_duplicates.csv", index=False)



    # ---------- 6. Tan du sau clean ----------

    res_cols = [c for c in df.columns if c.startswith("res_")]

    residue_summary = {c[4:]: {"files_affected": int((df[c] > 0).sum()),

                               "total_hits": int(df[c].sum())} for c in res_cols}

    df[["filename"] + res_cols].to_csv(out / "residue_per_file.csv", index=False)



    # ---------- 7. Nhan chu de ----------

    label_block = None

    labels = None

    label_validation = None

    if args.labels:

        lab, label_diag = load_labels(Path(args.labels))

        m = df.merge(lab, on="stem", how="left", validate="one_to_one")

        missing = int(m["label"].isna().sum())

        dataset_stems = set(df["stem"])
        labels_not_in_dataset = lab[~lab["stem"].isin(dataset_stems)].copy()
        labels_not_in_dataset.to_csv(out / "labels_not_in_dataset.csv", index=False)
        label_diag["duplicate_rows"].to_csv(out / "label_duplicate_entries.csv", index=False)

        coverage = m[["filename", "stem", "label"]].copy()
        coverage["status"] = "ok"
        coverage.loc[coverage["label"].isna(), "status"] = "missing_label"
        coverage.loc[coverage["stem"].isin(label_diag["conflicting_stems"]), "status"] = "conflicting_labels"
        coverage.to_csv(out / "label_coverage.csv", index=False)
        label_validation = {
            "input_label_rows": label_diag["input_rows"],
            "unique_label_files": int(len(lab)),
            "duplicate_label_rows": int(len(label_diag["duplicate_rows"])),
            "conflicting_label_files": int(len(label_diag["conflicting_stems"])),
            "dataset_files_without_label": missing,
            "label_files_not_in_dataset": int(len(labels_not_in_dataset)),
            "rows_without_filename": label_diag["rows_without_filename"],
            "coverage_pct": float(100 * (len(df) - missing) / max(len(df), 1)),
            "label_alias_rules": LABEL_ALIASES,
        }

        m["label"] = m["label"].fillna("__missing__")

        labels = m["label"].values

        m.drop(columns=[c for c in m.columns if c.startswith("res_")]).to_csv(

            out / "docs_with_labels.csv", index=False)



        grp = m.groupby("label")["n_words"].agg(["count", "mean", "median"]).sort_values(

            "count", ascending=False)

        grp["share_pct"] = 100 * grp["count"] / grp["count"].sum()

        label_validation["labels_without_english_display_name"] = sorted(
            label for label in grp.index if label != "__missing__" and label not in LABEL_EN_MAP
        )

        grp.to_csv(out / "label_distribution.csv")



        # tu dac trung moi chu de (trung binh TF-IDF)

        top_terms_rows = []

        for l in grp.index:

            sel = np.where(labels == l)[0]

            mean_vec = np.asarray(X[sel].mean(axis=0)).ravel()

            top = terms[np.argsort(-mean_vec)[:12]]

            top_terms_rows.append({"label": l, "n_docs": len(sel), "top_terms": ", ".join(top)})

        pd.DataFrame(top_terms_rows).to_csv(out / "label_top_terms.csv", index=False)



        grp_plot = grp["count"].copy().iloc[::-1]
        plot_labels = [LABEL_EN_MAP.get(label, label) for label in grp_plot.index]

        fig, ax = plt.subplots(figsize=(10.5, 6))
        bars = ax.barh(plot_labels, grp_plot.values, color="#2b5c8f", edgecolor="white", height=0.65, zorder=3)
        bars[-1].set_color("#1e3a8a")

        max_val = grp_plot.max()
        for bar in bars:
            val = int(bar.get_width())
            pct = val / len(df) * 100
            ax.text(val + max_val * 0.012, bar.get_y() + bar.get_height() / 2,
                    f" {val} ({pct:.1f}%)", va="center", ha="left",
                    fontsize=9.5, fontweight="semibold", color="#2d3748")

        ax.set_xlim(0, max_val * 1.15)
        n_named_labels = int(sum(label != "__missing__" for label in grp.index))
        ax.set_title(f"PHÂN BỐ {len(df):,} VĂN BẢN THEO {n_named_labels} NHÃN NỘI DUNG", fontsize=12, fontweight="bold", pad=12, color="#1a202c")
        ax.set_xlabel("Số lượng văn bản (Documents)", fontsize=10.5, labelpad=8)
        ax.set_ylabel("Thể loại nội dung", fontsize=10.5, labelpad=8)
        ax.grid(axis="x", linestyle="--", alpha=0.35, zorder=0)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        plt.savefig(out / "fig_label_counts.png", dpi=300)
        plt.close()

        conf_stats = None
        if "confidence_level" in m.columns:
            order = ["low", "medium", "high"]
            conf_values = m["confidence_level"].astype("string").str.strip().str.lower()
            conf_values = conf_values.mask(conf_values == "", pd.NA)
            conf_known = conf_values.value_counts().reindex(order, fill_value=0)
            conf_missing = int(conf_values.isna().sum())
            conf_other = int((conf_values.notna() & ~conf_values.isin(order)).sum())
            conf_counts = pd.Series(
                [*conf_known.values, conf_other, conf_missing],
                index=[*order, "other_or_invalid", "missing"], dtype=int
            )
            conf_stats = {str(k): int(v) for k, v in conf_counts.items()}
            fig, ax = plt.subplots(figsize=(7.5, 4.8))
            labels_vi = ["Thấp", "Trung bình", "Cao", "Khác", "Thiếu"]
            colors = ["#f59e0b", "#3b82f6", "#059669", "#94a3b8", "#64748b"]
            x_pos = np.arange(len(conf_counts))
            bars = ax.bar(x_pos, conf_counts.values, color=colors, edgecolor="white", width=0.55, zorder=3)
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, h + max(conf_counts.values.max(), 1) * 0.015,
                        f"{int(h)} ({h / len(df) * 100:.1f}%)", ha="center", va="bottom",
                        fontsize=9.5, fontweight="semibold", color="#1f2937")
            ax.set_xticks(x_pos)
            ax.set_xticklabels(labels_vi, fontsize=9.5)
            ax.set_ylim(0, max(conf_counts.values.max(), 1) * 1.18)
            ax.set_title("MỨC TIN CẬY ĐƯỢC GHI TRONG TỆP NHÃN", fontsize=12, fontweight="bold", pad=12, color="#1a202c")
            ax.set_xlabel("Mức được ghi trong dữ liệu nhãn; không phải độ chính xác mô hình", fontsize=10.5, labelpad=8)
            ax.set_ylabel("Số lượng văn bản (Documents)", fontsize=10.5, labelpad=8)
            ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            plt.savefig(out / "fig_confidence.png", dpi=300)
            plt.close()
        elif "confidence" in m.columns:
            conf = pd.to_numeric(m["confidence"], errors="coerce")
            conf_counts = conf.value_counts().sort_index()
            conf_stats = conf_counts.to_dict()

            fig, ax = plt.subplots(figsize=(7.5, 4.8))
            level_labels = {level: str(level) for level in range(1, 6)}
            palette = ["#9ca3af", "#f59e0b", "#3b82f6", "#10b981", "#059669"]
            x_pos = np.arange(len(conf_counts))
            bars = ax.bar(x_pos, conf_counts.values, color="#3182ce", edgecolor="white", width=0.55, zorder=3)
            for idx_b, b in enumerate(bars):
                if idx_b < len(palette):
                    b.set_color(palette[idx_b])

            for bar in bars:
                h = bar.get_height()
                pct = h / len(df) * 100
                ax.text(bar.get_x() + bar.get_width() / 2, h + max(conf_counts.values) * 0.015,
                        f"{int(h)} ({pct:.1f}%)", ha="center", va="bottom",
                        fontsize=9.5, fontweight="semibold", color="#1f2937")

            ax.set_xticks(x_pos)
            ax.set_xticklabels([level_labels.get(int(k), str(k)) for k in conf_counts.index], fontsize=9.5)
            ax.set_ylim(0, max(conf_counts.values) * 1.18)
            ax.set_title("PHÂN BỐ GIÁ TRỊ CONFIDENCE TRONG TỆP NHÃN", fontsize=12, fontweight="bold", pad=12, color="#1a202c")
            ax.set_xlabel("Giá trị confidence được ghi trong dữ liệu nhãn (1 - 5)", fontsize=10.5, labelpad=8)
            ax.set_ylabel("Số lượng văn bản (Documents)", fontsize=10.5, labelpad=8)
            ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            plt.savefig(out / "fig_confidence.png", dpi=300)
            plt.close()



        label_block = {"n_labels": n_named_labels, "missing_label_files": missing,

                       "smallest_label_count": int(grp["count"].min()),

                       "labels_below_2pct": grp[grp["share_pct"] < 2].index.tolist(),

                       "confidence_counts": conf_stats,

                       "validation": label_validation}



    # ---------- 8. KMeans (kiem tra cheo nhan) + scatter 2D ----------

    print("KMeans + SVD ...")

    n_comp = int(min(100, X.shape[1] - 1, X.shape[0] - 1))

    svd = TruncatedSVD(n_components=n_comp, random_state=0)

    Z = normalize(svd.fit_transform(X))

    sil_rows = []

    k_max = min(args.k_max, len(df) - 1)

    for k in range(args.k_min, k_max + 1):
        try:
            km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Z)
            n_clusters_found = len(np.unique(km.labels_))
            if 2 <= n_clusters_found < len(df):
                score = float(silhouette_score(Z, km.labels_))
                status = "ok"
            else:
                score = None
                status = "invalid_cluster_count"
            sil_rows.append({"k": k, "silhouette": score,
                             "clusters_found": n_clusters_found, "status": status})
        except ValueError as exc:
            sil_rows.append({"k": k, "silhouette": None, "clusters_found": None,
                             "status": f"error: {exc}"})

    sil = pd.DataFrame(sil_rows)

    sil.to_csv(out / "kmeans_silhouette.csv", index=False)

    kmeans_block = {"svd_components": n_comp,
                    "silhouette_by_k": sil.to_dict("records"),
                    "interpretation": "Chi so tham khao mo ta cau truc gom cum; khong phai accuracy phan loai."}

    valid_sil = sil.dropna(subset=["silhouette"]) if "silhouette" in sil else pd.DataFrame()
    if len(valid_sil):

        best_k = int(valid_sil.loc[valid_sil["silhouette"].idxmax(), "k"])

        kmeans_block["best_k_by_silhouette"] = best_k

    if labels is not None:
        valid_label_mask = labels != "__missing__"
        valid_label_values = labels[valid_label_mask]
        k_lab = len(set(valid_label_values))
        if k_lab >= 1 and int(valid_label_mask.sum()) >= 2:
            km_lab = KMeans(n_clusters=max(k_lab, 2), n_init=10, random_state=0).fit(Z)
            kmeans_block["k_equal_n_labels"] = k_lab
            kmeans_block["documents_compared_to_labels"] = int(valid_label_mask.sum())
            kmeans_block["unlabeled_documents_excluded"] = int((~valid_label_mask).sum())
            kmeans_block["NMI_vs_labels"] = float(normalized_mutual_info_score(
                valid_label_values, km_lab.labels_[valid_label_mask]))
            kmeans_block["ARI_vs_labels"] = float(adjusted_rand_score(
                valid_label_values, km_lab.labels_[valid_label_mask]))
            pd.crosstab(valid_label_values, km_lab.labels_[valid_label_mask]).to_csv(
                out / "label_vs_kmeans_crosstab.csv")



    svd_2d = TruncatedSVD(n_components=2, random_state=0)
    p2 = svd_2d.fit_transform(X)
    svd_2d_variance = [float(v) for v in svd_2d.explained_variance_ratio_]
    fig, ax = plt.subplots(figsize=(10.5, 7.5))
    if labels is not None:
        cmap = plt.colormaps.get_cmap("tab20")
        unique_labels = sorted(set(labels))
        for idx_l, l in enumerate(unique_labels):
            sel = labels == l
            ax.scatter(p2[sel, 0], p2[sel, 1], s=18, alpha=0.8, color=cmap(idx_l % 20),
                       label=f"{LABEL_EN_MAP.get(l, l)} (n={sel.sum()})", edgecolors="none")
        ax.legend(fontsize=8.5, markerscale=1.4, loc="upper right",
                  framealpha=0.92, facecolor="white", edgecolor="#cbd5e1", title="Thể loại (Categories)", title_fontsize=9.5)
    else:
        ax.scatter(p2[:, 0], p2[:, 1], s=18, alpha=0.7, color="#2b5c8f")
    ax.set_title("BIỂU DIỄN TF-IDF CỦA 1.000 VĂN BẢN QUA SVD 2D", fontsize=12, fontweight="bold", pad=12, color="#1a202c")
    ax.set_xlabel("Thành phần SVD 1", fontsize=10.5, labelpad=8)
    ax.set_ylabel("Thành phần SVD 2", fontsize=10.5, labelpad=8)
    ax.grid(True, linestyle=":", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(out / "fig_svd_scatter.png", dpi=300)
    plt.close()



    # ---------- 9. Luu tong ket ----------

    summary = {
               "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
               "run_metadata": {
                   "data_dir": str(data_dir),
                   "input_pattern": input_pattern,
                   "labels_file": str(Path(args.labels).resolve()) if args.labels else None,
                   "output_dir": str(out.resolve()),
                   "script_path": str(Path(__file__).resolve()),
                   "n_input_files": int(len(files)),
                   "input_encodings": dict(encoding_counts),
                   "platform": platform.platform(),
                   "python_version": platform.python_version(),
                   "numpy_version": np.__version__,
                   "pandas_version": pd.__version__,
                   "matplotlib_version": matplotlib.__version__,
                   "scikit_learn_version": sklearn.__version__,
                   "scipy_version": scipy.__version__,
                   "nltk_version": nltk.__version__,
               },
               "method": {
                   "word_count_regex": WORD_RE.pattern,
                   "min_words": int(args.min_words),
                   "words_per_page_assumption": int(args.words_per_page),
                   "stopword_source": "scikit-learn ENGLISH_STOP_WORDS + EXTRA_STOP",
                   "stemming": "NLTK PorterStemmer",
                   "zipf_reference": "f(1)/rank; visual reference only, no exponent fitted",
                   "tfidf": {
                       "min_df": 3, "max_df": 0.6, "sublinear_tf": True,
                       "use_idf": True, "smooth_idf": True, "norm": "l2",
                   },
                   "near_duplicate_cosine_threshold": float(args.dup_threshold),
                   "exact_duplicate_hash": "SHA-256 of normalized token sequence",
                   "label_aliases": LABEL_ALIASES,
               },
               "length": length_stats, "vocabulary": vocab_stats,

               "tfidf_vocab_size_(min_df=3,max_df=0.6)": int(X.shape[1]),

               "svd_2d_explained_variance_ratio": svd_2d_variance,

               "exact_duplicate_groups": exact,

               "near_duplicate_pairs_(cos>%.2f)" % args.dup_threshold: int(len(near)),

               "residue": residue_summary, "labels": label_block, "kmeans": kmeans_block}

    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),

                                      encoding="utf-8")

    df.drop(columns=res_cols).to_csv(out / "doc_stats.csv", index=False)



    print("\n===== TOM TAT =====")

    print(json.dumps(summary, indent=2, ensure_ascii=False)[:6000])

    print(f"\nTat ca file dau ra nam trong: {out.resolve()}")

    if length_stats["files_below_12000"]:

        print(f"\n[CANH BAO] {length_stats['files_below_12000']} file duoi {args.min_words} tu "

              f"-> xem files_below_min_length.csv")





if __name__ == "__main__":

    main()

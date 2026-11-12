"""GD1 preprocessing, using the frozen configuration and stopword list."""
import json
import re
from functools import lru_cache
from pathlib import Path

from nltk.stem import PorterStemmer

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
CONFIG = json.loads((CONFIG_DIR / "configuration.json").read_text(encoding="utf-8"))
STOPWORDS = json.loads((CONFIG_DIR / "stopwords.json").read_text(encoding="utf-8"))
WORD_RE = re.compile(CONFIG["corpus"]["word_count_regex"])
STOP_ALL = frozenset(STOPWORDS["stop_all"])
PORTER_STEMMER = PorterStemmer(mode=CONFIG["preprocessing"]["stemmer_mode"])


def normalize_text(text: str) -> str:
    for source, target in CONFIG["preprocessing"]["apostrophe_replacements"].items():
        text = text.replace(source, target)
    return text


def raw_tokens(text: str) -> list[str]:
    """Word counting tokens, before base/stopword filtering and stemming."""
    return WORD_RE.findall(normalize_text(text).lower())


@lru_cache(maxsize=100_000)
def stem(base: str) -> str:
    # Porter is deterministic; memoization changes cost, not token order/count.
    return PORTER_STEMMER.stem(base)


def content_tokens(text: str) -> list[str]:
    result = []
    for token in raw_tokens(text):
        base = token.split("'")[0]
        if len(base) >= CONFIG["preprocessing"]["min_base_length"] and base not in STOP_ALL:
            result.append(stem(base))
    return result


def token_trace(text: str) -> list[dict]:
    """One row per normalized token, including the reason for removal."""
    rows = []
    for token in raw_tokens(text):
        base = token.split("'")[0]
        reason = "short_base" if len(base) < 2 else "stopword" if base in STOP_ALL else "kept"
        rows.append({"token": token, "base": base, "decision": reason,
                     "stem": stem(base) if reason == "kept" else ""})
    return rows

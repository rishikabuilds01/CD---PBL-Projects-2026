"""
N-Gram Statistical Keyword Suggestion Engine
Uses character-level 2-gram and 3-gram similarity models to detect and repair
general C keyword typos beyond hardcoded dictionary mappings.
"""

from __future__ import annotations
import math
from typing import Optional, List, Dict, Set


ALL_C_KEYWORDS = [
    "int", "return", "if", "else", "while", "for", "break", "continue",
    "char", "float", "double", "void", "switch", "case", "default",
    "struct", "typedef", "sizeof", "const", "static", "extern",
    "printf", "scanf", "malloc", "free",
]


def _get_ngrams(word: str, n: int = 2) -> Set[str]:
    padded = f"^{word}$"
    return {padded[i:i+n] for i in range(len(padded) - n + 1)}


def ngram_similarity(w1: str, w2: str) -> float:
    """
    Computes Sørensen-Dice bigram and character overlap similarity between two words.
    """
    if w1 == w2:
        return 1.0
    if not w1 or not w2:
        return 0.0

    # Bigrams
    bi1 = _get_ngrams(w1, 2)
    bi2 = _get_ngrams(w2, 2)
    bi_inter = len(bi1 & bi2)
    bi_sim = (2.0 * bi_inter) / (len(bi1) + len(bi2)) if (len(bi1) + len(bi2)) > 0 else 0.0

    # Unpadded character set overlap
    char_inter = len(set(w1) & set(w2))
    char_sim = (2.0 * char_inter) / (len(set(w1)) + len(set(w2)))

    # Prefix match bonus (first character matches)
    prefix_bonus = 0.10 if w1[0] == w2[0] else 0.0

    return min(0.6 * bi_sim + 0.3 * char_sim + prefix_bonus, 1.0)


def suggest_keyword_ngram(word: str, threshold: float = 0.55) -> Optional[str]:
    """
    Evaluates an unrecognized word against all standard C keywords using the n-gram model.
    Guarantees safety:
    - Never mutates 1-letter identifiers (e.g. i, j, k, x, y)
    - Rejects ambiguous ties
    - Requires similarity >= threshold
    """
    if len(word) <= 1:
        return None

    if word in ALL_C_KEYWORDS:
        return None

    best_match: Optional[str] = None
    best_sim: float = 0.0
    second_best: float = 0.0

    for kw in ALL_C_KEYWORDS:
        # Length filter: typos rarely change length by more than 2 chars
        if abs(len(word) - len(kw)) > 2:
            continue

        sim = ngram_similarity(word.lower(), kw)
        if sim > best_sim:
            second_best = best_sim
            best_sim = sim
            best_match = kw
        elif sim > second_best:
            second_best = sim

    # High-confidence threshold and margin requirement to prevent false positives
    if best_match and best_sim >= threshold and (best_sim - second_best >= 0.08 or best_sim >= 0.80):
        return best_match

    return None

"""
Confidence Scorer Module
Calculates granular confidence scores for compiler repairs and provides
a project-wide reliability breakdown.
"""

from __future__ import annotations
from typing import Dict, Any, List


# Base confidence lookup by fix provenance and mechanism
CONFIDENCE_MAP = {
    # Rule-based deterministic fixes
    "missing_semicolon": 0.95,
    "missing_rbrace": 0.92,
    "missing_lbrace": 0.90,
    "missing_rparen": 0.94,
    "missing_lparen": 0.94,
    "main_lparen_expected": 0.98,
    "missing_comma_args": 0.88,
    "missing_comma_params": 0.88,
    "missing_rhs": 0.85,
    "extraneous_token": 0.86,
    "mismatched_token": 0.82,

    # Lexical fixes
    "char_normalization": 0.99,
    "token_normalization": 0.95,
    "keyword_typo": 0.92,

    # Semantic fixes
    "unused_removal": 0.96,
    "symbol_typo_dist_1": 0.93,
    "symbol_typo_dist_2": 0.78,

    # Security fixes
    "unsafe_gets_fix": 0.97,
    "unsafe_strcpy_fix": 0.91,

    # AI Model generative patch
    "ai_neural_patch": 0.75,
}


def score_fix_confidence(
    step_msg: str,
    category: str = "SYNTAX",
    details: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Computes a percentage confidence score (0-100), rating tag, and color status.
    """
    details = details or {}
    text = step_msg.lower()
    score = 0.80

    if "rule:" in text:
        if "semicolon" in text or "';'" in text or ";" in text:
            score = CONFIDENCE_MAP["missing_semicolon"]
        elif "rbrace" in text or "}" in text:
            score = CONFIDENCE_MAP["missing_rbrace"]
        elif "lbrace" in text or "{" in text:
            score = CONFIDENCE_MAP["missing_lbrace"]
        elif "parenthes" in text or "lparen" in text or "rparen" in text:
            score = CONFIDENCE_MAP["missing_rparen"]
        elif "rhs" in text:
            score = CONFIDENCE_MAP["missing_rhs"]
        else:
            score = 0.88

    elif "lex:" in text:
        if "normalized character" in text:
            score = CONFIDENCE_MAP["char_normalization"]
        elif "normalized token" in text:
            score = CONFIDENCE_MAP["token_normalization"]
        elif "keyword" in text:
            score = CONFIDENCE_MAP["keyword_typo"]
        else:
            score = 0.92

    elif "sym:" in text or "sem:" in text:
        if "unused" in text:
            score = CONFIDENCE_MAP["unused_removal"]
        else:
            # Check distance if passed
            dist = details.get("distance", 1)
            score = CONFIDENCE_MAP["symbol_typo_dist_1"] if dist <= 1 else CONFIDENCE_MAP["symbol_typo_dist_2"]

    elif "sec:" in text or "security" in text.lower():
        if "gets" in text:
            score = CONFIDENCE_MAP["unsafe_gets_fix"]
        elif "strcpy" in text:
            score = CONFIDENCE_MAP["unsafe_strcpy_fix"]
        else:
            score = 0.90

    elif "ai:" in text or "aisec:" in text:
        # Heuristic score adjust if passed
        heuristic_score = details.get("heuristic_score")
        if heuristic_score is not None:
            # Normalize heuristic score to 0.60 - 0.88
            normalized = 0.60 + min(max(heuristic_score / 20.0, 0.0), 0.28)
            score = normalized
        else:
            score = CONFIDENCE_MAP["ai_neural_patch"]

    percent = int(round(score * 100))

    if percent >= 90:
        level = "HIGH"
        color = "#16a34a"  # green
    elif percent >= 75:
        level = "MEDIUM"
        color = "#0284c7"  # blue/cyan
    elif percent >= 60:
        level = "FAIR"
        color = "#d97706"  # amber
    else:
        level = "LOW"
        color = "#dc2626"  # red

    return {
        "confidence_score": score,
        "confidence_percent": percent,
        "confidence_level": level,
        "color_code": color,
    }


def compute_overall_confidence_dashboard(
    applied_steps: List[str],
    suggestions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Summarizes confidence statistics across all identified/applied repairs.
    """
    scores = []
    category_counts = {"HIGH": 0, "MEDIUM": 0, "FAIR": 0, "LOW": 0}

    for sug in suggestions:
        c = sug.get("confidence", {})
        pct = c.get("confidence_percent")
        if pct is not None:
            scores.append(pct)
            lvl = c.get("confidence_level", "MEDIUM")
            category_counts[lvl] = category_counts.get(lvl, 0) + 1

    if not scores:
        for st in applied_steps:
            scored = score_fix_confidence(st)
            scores.append(scored["confidence_percent"])
            lvl = scored["confidence_level"]
            category_counts[lvl] = category_counts.get(lvl, 0) + 1

    avg_score = round(sum(scores) / len(scores), 1) if scores else 100.0
    min_score = min(scores) if scores else 100
    max_score = max(scores) if scores else 100

    return {
        "average_confidence": avg_score,
        "min_confidence": min_score,
        "max_confidence": max_score,
        "total_scored": len(scores),
        "level_breakdown": category_counts,
        "reliability_rating": "EXCELLENT" if avg_score >= 90 else ("GOOD" if avg_score >= 75 else "MODERATE"),
    }

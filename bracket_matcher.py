"""
Bracket & Brace Stack Matcher
Performs full-file stack analysis to detect and repair:
1. Mismatched bracket types: (], {), [}
2. Missing closing brackets: unclosed {, (, [
3. Extraneous/orphaned closing brackets: rogue }, ), ]
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any


@dataclass
class BracketToken:
    char: str
    line: int
    col: int
    index: int


MATCHING_PAIRS = {
    "(": ")",
    "{": "}",
    "[": "]",
}

OPENING_BRACKETS = set(MATCHING_PAIRS.keys())
CLOSING_BRACKETS = set(MATCHING_PAIRS.values())
REVERSE_PAIRS = {v: k for k, v in MATCHING_PAIRS.items()}


def scan_bracket_stack(source_text: str) -> Dict[str, Any]:
    """
    Scans source code ignoring strings and comments, tracking balance and mismatches.
    """
    stack: List[BracketToken] = []
    mismatches: List[Dict[str, Any]] = []
    unclosed: List[BracketToken] = []
    unopened: List[BracketToken] = []

    # Strip comments and strings while preserving exact character indices and line/col
    clean_chars = list(source_text)
    n = len(source_text)
    i = 0
    line = 1
    col = 0

    while i < n:
        ch = source_text[i]
        col += 1

        if ch == "\n":
            line += 1
            col = 0
            i += 1
            continue

        # Skip line comment
        if ch == "/" and i + 1 < n and source_text[i + 1] == "/":
            while i < n and source_text[i] != "\n":
                clean_chars[i] = " "
                i += 1
            continue

        # Skip block comment
        if ch == "/" and i + 1 < n and source_text[i + 1] == "*":
            clean_chars[i] = " "
            clean_chars[i + 1] = " "
            i += 2
            while i + 1 < n and not (source_text[i] == "*" and source_text[i + 1] == "/"):
                if source_text[i] == "\n":
                    line += 1
                    col = 0
                clean_chars[i] = " "
                i += 1
            if i + 1 < n:
                clean_chars[i] = " "
                clean_chars[i + 1] = " "
                i += 2
            continue

        # Skip string literal
        if ch == '"':
            clean_chars[i] = " "
            i += 1
            while i < n and source_text[i] != '"':
                if source_text[i] == "\\" and i + 1 < n:
                    clean_chars[i] = " "
                    clean_chars[i + 1] = " "
                    i += 2
                    continue
                clean_chars[i] = " "
                i += 1
            if i < n:
                clean_chars[i] = " "
                i += 1
            continue

        # Skip character literal
        if ch == "'":
            clean_chars[i] = " "
            i += 1
            while i < n and source_text[i] != "'":
                if source_text[i] == "\\" and i + 1 < n:
                    clean_chars[i] = " "
                    clean_chars[i + 1] = " "
                    i += 2
                    continue
                clean_chars[i] = " "
                i += 1
            if i < n:
                clean_chars[i] = " "
                i += 1
            continue

        # Check brackets
        if ch in OPENING_BRACKETS:
            stack.append(BracketToken(ch, line, col, i))
        elif ch in CLOSING_BRACKETS:
            if not stack:
                unopened.append(BracketToken(ch, line, col, i))
            else:
                top = stack[-1]
                expected_close = MATCHING_PAIRS[top.char]
                if ch == expected_close:
                    stack.pop()
                else:
                    # Type mismatch (e.g. opened with '{' but encountered ')')
                    mismatches.append({
                        "open_token": top,
                        "close_token": BracketToken(ch, line, col, i),
                        "expected": expected_close,
                        "found": ch,
                    })
                    stack.pop()
        i += 1

    unclosed = stack

    return {
        "is_balanced": len(unclosed) == 0 and len(unopened) == 0 and len(mismatches) == 0,
        "unclosed_count": len(unclosed),
        "unopened_count": len(unopened),
        "mismatch_count": len(mismatches),
        "unclosed": unclosed,
        "unopened": unopened,
        "mismatches": mismatches,
    }


def repair_bracket_imbalance(source_text: str) -> Tuple[str, List[str]]:
    """
    Repairs structural bracket mismatches and imbalances across the whole file.
    """
    analysis = scan_bracket_stack(source_text)
    if analysis["is_balanced"]:
        return source_text, []

    fixes = []
    modified = source_text

    # 1. Fix direct type mismatches (e.g. `( ... }` -> `( ... )`)
    for mm in analysis["mismatches"]:
        open_tok: BracketToken = mm["open_token"]
        close_tok: BracketToken = mm["close_token"]
        expected = mm["expected"]
        idx = close_tok.index

        if idx < len(modified) and modified[idx] == close_tok.char:
            modified = modified[:idx] + expected + modified[idx + 1:]
            fixes.append(
                f"repaired mismatched bracket at line {close_tok.line}: changed '{close_tok.char}' to '{expected}' to match '{open_tok.char}' from line {open_tok.line}"
            )

    # 2. Re-scan to handle remaining unclosed/unopened brackets
    analysis2 = scan_bracket_stack(modified)

    # 3. Handle unclosed brackets by appending their respective closures
    for unclosed_tok in reversed(analysis2["unclosed"]):
        expected = MATCHING_PAIRS[unclosed_tok.char]
        if expected == "}":
            if not modified.endswith("\n"):
                modified += "\n"
            modified += "}\n"
            fixes.append(f"appended missing closing brace '}}' for block opened at line {unclosed_tok.line}")
        elif expected == ")":
            # Append parenthesis at the end of the unclosed token's line
            lines = modified.splitlines(keepends=True)
            t_idx = unclosed_tok.line - 1
            if 0 <= t_idx < len(lines):
                line_str = lines[t_idx]
                r_pos = len(line_str.rstrip("\r\n"))
                lines[t_idx] = line_str[:r_pos] + ")" + line_str[r_pos:]
                modified = "".join(lines)
                fixes.append(f"inserted missing closing parenthesis ')' on line {unclosed_tok.line}")

    return modified, fixes

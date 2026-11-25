"""
AI Error Explainer Module
Generates human-readable, educational explanations for compiler errors,
syntax violations, and security warnings in C programs.
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, Tuple


# Educational explanation knowledge-base for C compiler error causes and resolutions
EXPLANATION_CATALOG = {
    "missing_semicolon": {
        "title": "Missing Statement Terminator (Semicolon)",
        "why": "In C, statements (such as variable assignments, function calls, and return statements) must end with a semicolon (`;`). Without it, the compiler attempts to parse the next line as a continuation of the current statement.",
        "fix_summary": "Appended `;` to terminate the statement.",
        "pedagogical_tip": "Remember that preprocessor directives (#include, #define) and control block headers (if, while, for) do not end with a semicolon, but standard statements always do."
    },
    "missing_rbrace": {
        "title": "Unclosed Compound Statement Block",
        "why": "A closing curly brace (`}`) is missing. Every opening brace `{` that begins a function or control block requires a matching closing brace to mark where that block ends.",
        "fix_summary": "Inserted missing `}` at the appropriate scope boundary.",
        "pedagogical_tip": "Good code indentation helps spot unclosed curly braces easily."
    },
    "missing_lbrace": {
        "title": "Missing Opening Block Brace",
        "why": "The compiler encountered statement bodies or function headers where an opening brace `{` was expected to enclose executable statements.",
        "fix_summary": "Inserted missing `{` to start the block.",
        "pedagogical_tip": "Function definitions and multi-statement loops/conditionals must open with `{`."
    },
    "missing_rparen": {
        "title": "Unclosed Parenthesis",
        "why": "An opening parenthesis `(` for an expression or parameter list was never closed with a matching `)` before the end of the line or statement.",
        "fix_summary": "Inserted closing parenthesis `)`.",
        "pedagogical_tip": "Parentheses must always be balanced in mathematical expressions and parameter lists."
    },
    "missing_lparen": {
        "title": "Missing Opening Parenthesis",
        "why": "A function call or control statement header (e.g. `main`, `if`, `while`) is missing its opening parenthesis.",
        "fix_summary": "Inserted missing `(`.",
        "pedagogical_tip": "Control statements like `if (...)` and function definitions like `main()` always require parentheses."
    },
    "main_lparen_expected": {
        "title": "Malformed main() Signature",
        "why": "The entry point function `main` is missing its parameter parentheses `()`.",
        "fix_summary": "Replaced with standard entry signature `main()`.",
        "pedagogical_tip": "Standard C entry points should be declared as `int main()` or `int main(int argc, char *argv[])`."
    },
    "missing_comma_args": {
        "title": "Missing Argument Separator",
        "why": "Multiple arguments passed to a function call must be separated by commas (`,`).",
        "fix_summary": "Inserted comma `,` between arguments.",
        "pedagogical_tip": "Ensure consecutive parameters or arguments are delineated with commas."
    },
    "missing_comma_params": {
        "title": "Missing Parameter Separator in Function Declaration",
        "why": "Parameters in a function signature must be separated by commas.",
        "fix_summary": "Inserted comma `,` between function parameters.",
        "pedagogical_tip": "For example: `void func(int a, int b)`."
    },
    "missing_rhs": {
        "title": "Incomplete Assignment or Expression",
        "why": "An assignment operator (`=`) or binary operator was left without a right-hand side operand before `;`.",
        "fix_summary": "Provided a safe default right-hand side value (0 or null identifier).",
        "pedagogical_tip": "Every binary operator needs both operands to form a valid expression."
    },
    "extraneous_token": {
        "title": "Extraneous / Redundant Syntax Token",
        "why": "The compiler encountered an unexpected token that does not belong in the current grammatical construct.",
        "fix_summary": "Removed the extraneous token to restore grammar alignment.",
        "pedagogical_tip": "Check for accidental double punctuation or stray characters."
    },
    "mismatched_token": {
        "title": "Mismatched Syntax Token",
        "why": "The token present at this location does not match the token expected by the C grammar.",
        "fix_summary": "Replaced or aligned the mismatched token with standard grammar.",
        "pedagogical_tip": "Check the surrounding tokens to ensure matching pairs (such as `[]` vs `()`)."
    },
    "undeclared": {
        "title": "Undeclared Identifier",
        "why": "The identifier used in this statement was never declared in the current or outer scope.",
        "fix_summary": "Corrected the identifier to the closest matching declared variable in scope.",
        "pedagogical_tip": "In C, variables must be declared with their data type before they can be read or assigned."
    },
    "unused": {
        "title": "Unused Variable Declaration",
        "why": "A variable was declared and allocated stack memory, but is never referenced anywhere in the program.",
        "fix_summary": "Removed redundant variable declaration to optimize memory and maintain clean code.",
        "pedagogical_tip": "Unused variables clutter code and can produce compiler warnings (`-Wunused-variable`)."
    },
    "unsafe_gets": {
        "title": "Security Vulnerability: Unbounded Buffer Read",
        "why": "The function `gets()` does not perform boundary checks on the target buffer, making the application vulnerable to buffer overflow attacks.",
        "fix_summary": "Replaced `gets(buf)` with `fgets(buf, sizeof(buf), stdin)`.",
        "pedagogical_tip": "`gets` was removed from the ISO C11 standard due to unavoidable security vulnerabilities."
    },
    "unsafe_strcpy": {
        "title": "Security Vulnerability: Potential Buffer Overflow",
        "why": "`strcpy` copies a null-terminated string without verifying that the destination buffer is large enough.",
        "fix_summary": "Replaced `strcpy` with bounded `strncpy`.",
        "pedagogical_tip": "Always bound string copies using buffer capacity limits."
    }
}


def explain_error(
    category: str,
    raw_step_or_reason: str,
    original_code: str = "",
    fixed_code: str = "",
    line_number: int = 1,
) -> Dict[str, Any]:
    """
    Produces a detailed, context-aware explanation dictionary for an error and its applied fix.
    """
    key = _identify_explanation_key(raw_step_or_reason, category)
    info = EXPLANATION_CATALOG.get(key)

    if not info:
        # Fallback dynamic generator
        title = f"{category.capitalize()} Notice at Line {line_number}"
        why = f"The compiler encountered an irregularity: {raw_step_or_reason}."
        fix = f"Adapted syntax on line {line_number} to satisfy compiler constraints."
        tip = "Inspect syntax around this line to conform with C standard grammar."
    else:
        title = info["title"]
        why = info["why"]
        fix = info["fix_summary"]
        tip = info["pedagogical_tip"]

    # Contextual personalization
    context_note = ""
    if original_code and fixed_code:
        orig_strip = original_code.strip()
        fixed_strip = fixed_code.strip()
        if orig_strip != fixed_strip:
            context_note = f"Transformed `{orig_strip}` into `{fixed_strip}`."

    return {
        "title": title,
        "why": why,
        "fix_summary": fix,
        "pedagogical_tip": tip,
        "context_note": context_note,
        "key": key,
    }


def _identify_explanation_key(text: str, category: str) -> str:
    s = text.lower()
    if "semicolon" in s or "missing ';'" in s or "inserted missing ';'" in s:
        return "missing_semicolon"
    if "missing '}'" in s or "missing_rbrace" in s:
        return "missing_rbrace"
    if "missing '{'" in s or "missing_lbrace" in s:
        return "missing_lbrace"
    if "missing ')'" in s or "missing_rparen" in s:
        return "missing_rparen"
    if "main_lparen" in s or "missing_lparen" in s:
        return "missing_lparen"
    if "missing_comma_args" in s:
        return "missing_comma_args"
    if "missing_comma_params" in s:
        return "missing_comma_params"
    if "missing_rhs" in s or "rhs" in s:
        return "missing_rhs"
    if "extraneous" in s or "delete" in s:
        return "extraneous_token"
    if "mismatched" in s:
        return "mismatched_token"
    if "undeclared" in s or "typo" in s or "sym:" in s:
        return "undeclared"
    if "unused" in s:
        return "unused"
    if "gets" in s:
        return "unsafe_gets"
    if "strcpy" in s:
        return "unsafe_strcpy"
    return "unknown"

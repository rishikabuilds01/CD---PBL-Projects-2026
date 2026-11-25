"""
Undeclared Function Prototype Generator
Detects calls to undeclared functions in C source code and automatically generates
forward declarations / function prototypes placed above main().
"""

from __future__ import annotations
import re
from typing import List, Dict, Tuple, Optional, Set


# Common standard library functions that have known prototypes
STDLIB_PROTOTYPES = {
    "printf": "int printf(const char *format, ...);",
    "scanf": "int scanf(const char *format, ...);",
    "malloc": "void *malloc(int size);",
    "free": "void free(void *ptr);",
    "strlen": "int strlen(const char *s);",
    "strcpy": "char *strcpy(char *dest, const char *src);",
    "exit": "void exit(int status);",
    "abs": "int abs(int n);",
}

# Regex matching function calls: identifier followed immediately by '('
FUNC_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)")
C_KEYWORDS = {
    "if", "while", "for", "switch", "return", "sizeof", "main"
}


def find_undeclared_function_calls(
    source_text: str,
    declared_function_names: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Finds function calls in code that are not declared or defined anywhere in the file.
    """
    declared = set(declared_function_names or set())
    # Also find function definitions in the file: e.g. int foo(...) or void bar(...)
    func_def_re = re.compile(r"\b(?:int|float|char|void)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    for m in func_def_re.finditer(source_text):
        declared.add(m.group(1))

    undeclared_calls = []
    lines = source_text.splitlines()

    for line_idx, line in enumerate(lines, 1):
        # Skip comment lines
        s = line.strip()
        if s.startswith("//") or s.startswith("/*") or s.startswith("#"):
            continue

        for m in FUNC_CALL_RE.finditer(line):
            func_name = m.group(1)
            raw_args = m.group(2).strip()

            if func_name in C_KEYWORDS:
                continue

            if func_name not in declared:
                # Infer argument count
                if not raw_args:
                    arg_count = 0
                else:
                    arg_count = len([a for a in raw_args.split(",") if a.strip()])

                undeclared_calls.append({
                    "name": func_name,
                    "line": line_idx,
                    "arg_count": arg_count,
                    "raw_args": raw_args,
                })

    return undeclared_calls


def generate_function_prototype(name: str, arg_count: int = 0) -> str:
    """
    Generates a standard C function forward declaration prototype.
    """
    if name in STDLIB_PROTOTYPES:
        return STDLIB_PROTOTYPES[name]

    if arg_count == 0:
        params = "void"
    elif arg_count == 1:
        params = "int a"
    else:
        params = ", ".join(f"int a{i+1}" for i in range(arg_count))

    return f"int {name}({params});"


def auto_insert_prototypes(source_text: str) -> Tuple[str, List[str]]:
    """
    Scans for undeclared function calls and inserts forward declaration prototypes at the top of the file.
    """
    calls = find_undeclared_function_calls(source_text)
    if not calls:
        return source_text, []

    # Deduplicate by function name, picking max arguments inferred
    needed_funcs: Dict[str, int] = {}
    for c in calls:
        name = c["name"]
        needed_funcs[name] = max(needed_funcs.get(name, 0), c["arg_count"])

    prototypes = [generate_function_prototype(name, count) for name, count in needed_funcs.items()]
    fixes = [f"auto-generated forward declaration prototype: {proto}" for proto in prototypes]

    # Find optimal insertion line (after includes/macros, before first function)
    lines = source_text.splitlines(keepends=True)
    insert_idx = 0
    for idx, l in enumerate(lines):
        s = l.strip()
        if s.startswith("#include") or s.startswith("#define"):
            insert_idx = idx + 1

    proto_block = "\n// Forward Declarations\n" + "\n".join(prototypes) + "\n\n"
    if insert_idx < len(lines):
        lines.insert(insert_idx, proto_block)
    else:
        lines.append(proto_block)

    return "".join(lines), fixes

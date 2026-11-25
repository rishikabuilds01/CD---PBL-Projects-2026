"""
Unit tests for Medium-Impact Features:
1. Bracket/Brace Stack Matcher (compiler/bracket_matcher.py)
2. N-Gram Keyword Suggestion (compiler/ngram_keyword_corrector.py)
3. Smart Semicolon Boundary Rules (compiler/error_corrector.py)
4. Undeclared Function Prototype Generator (compiler/prototype_generator.py)
"""

import unittest
from compiler.bracket_matcher import scan_bracket_stack, repair_bracket_imbalance
from compiler.ngram_keyword_corrector import suggest_keyword_ngram, ngram_similarity
from compiler.error_corrector import apply_correction
from compiler.error_classifier import classify_error_message
from compiler.prototype_generator import find_undeclared_function_calls, auto_insert_prototypes


class TestMediumImpactFeatures(unittest.TestCase):
    # 1. Bracket/Brace Stack Matcher Tests
    def test_bracket_stack_detects_mismatch(self):
        code = "int main() { return 0; )"
        res = scan_bracket_stack(code)
        self.assertFalse(res["is_balanced"])
        self.assertGreaterEqual(res["mismatch_count"], 1)

    def test_bracket_stack_repairs_mismatch(self):
        code = "int main() {\n    return 0;\n)"
        repaired, fixes = repair_bracket_imbalance(code)
        self.assertTrue(len(fixes) > 0)
        self.assertIn("}", repaired)

    def test_bracket_stack_handles_unclosed_block(self):
        code = "int main() {\n    int a = 10;\n"
        repaired, fixes = repair_bracket_imbalance(code)
        self.assertTrue(repaired.rstrip().endswith("}"))
        self.assertTrue(any("closing brace" in f for f in fixes))

    # 2. N-Gram Keyword Suggestion Tests
    def test_ngram_detects_typo(self):
        # 'swtich' is not in hardcoded 20-entry map
        self.assertEqual(suggest_keyword_ngram("swtich"), "switch")
        self.assertEqual(suggest_keyword_ngram("staitc"), "static")

    def test_ngram_safety_avoids_single_char(self):
        self.assertIsNone(suggest_keyword_ngram("i"))
        self.assertIsNone(suggest_keyword_ngram("x"))

    # 3. Smart Semicolon Boundary Tests
    def test_smart_semicolon_skips_preprocessor(self):
        code = "#include <stdio.h>\nint main() {\n    return 0;\n}"
        cl = classify_error_message("missing ';'")
        repaired, msg = apply_correction(code, 1, 1, cl)
        # Should not insert semicolon on line 1 (#include)
        self.assertNotIn("#include <stdio.h>;", repaired)

    def test_smart_semicolon_skips_for_header(self):
        code = "int main() {\n    for (int i = 0\n    return 0;\n}"
        cl = classify_error_message("missing ';'")
        repaired, msg = apply_correction(code, 2, 1, cl)
        # Semicolon should not be blindly appended inside open for header
        self.assertNotIn("for (int i = 0;", repaired)

    # 4. Undeclared Function Prototype Generator Tests
    def test_prototype_generator_finds_calls(self):
        code = "int main() {\n    calculate(10, 20);\n    return 0;\n}"
        calls = find_undeclared_function_calls(code)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["name"], "calculate")
        self.assertEqual(calls[0]["arg_count"], 2)

    def test_prototype_generator_auto_inserts(self):
        code = "#include <stdio.h>\nint main() {\n    solve(5);\n    return 0;\n}"
        repaired, fixes = auto_insert_prototypes(code)
        self.assertTrue(len(fixes) > 0)
        self.assertIn("int solve(int a);", repaired)


if __name__ == "__main__":
    unittest.main()

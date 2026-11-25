"""
Unit tests for AI Error Explainer, Confidence Scorer, and Error Dependency Graph.
"""

import unittest
from compiler.error_explainer import explain_error
from compiler.confidence_scorer import score_fix_confidence, compute_overall_confidence_dashboard
from compiler.dependency_graph import analyze_error_dependencies


class TestHighImpactFeatures(unittest.TestCase):
    def test_error_explainer_known_catalog(self):
        expl = explain_error(
            category="SYNTAX",
            raw_step_or_reason="RULE: inserted missing ';'",
            original_code="int a = 10",
            fixed_code="int a = 10;",
            line_number=2,
        )
        self.assertIn("Semicolon", expl["title"])
        self.assertTrue(len(expl["why"]) > 20)
        self.assertIn("semicolon", expl["pedagogical_tip"].lower())
        self.assertIn("Transformed `int a = 10` into `int a = 10;`", expl["context_note"])

    def test_error_explainer_fallback(self):
        expl = explain_error(
            category="CUSTOM",
            raw_step_or_reason="unknown_quirk_123",
            line_number=15,
        )
        self.assertIn("Line 15", expl["title"])
        self.assertIn("unknown_quirk_123", expl["why"])

    def test_confidence_scorer_rules(self):
        res1 = score_fix_confidence("RULE: inserted missing ';'")
        self.assertGreaterEqual(res1["confidence_percent"], 90)
        self.assertEqual(res1["confidence_level"], "HIGH")

        res2 = score_fix_confidence("AI: INS 10 ;")
        self.assertLessEqual(res2["confidence_percent"], 85)

    def test_confidence_dashboard(self):
        applied = ["RULE: inserted missing ';'", "LEX: corrected keyword typo 'whlie' -> 'while'"]
        suggestions = [
            {"confidence": {"confidence_percent": 95, "confidence_level": "HIGH"}},
            {"confidence": {"confidence_percent": 92, "confidence_level": "HIGH"}},
        ]
        dash = compute_overall_confidence_dashboard(applied, suggestions)
        self.assertGreaterEqual(dash["average_confidence"], 90)
        self.assertEqual(dash["reliability_rating"], "EXCELLENT")

    def test_dependency_graph_cascade_detection(self):
        raw_errors = [
            {"line": 5, "column": 10, "msg": "missing '}' at 'return'"},
            {"line": 8, "column": 4, "msg": "extraneous input 'int'"},
            {"line": 12, "column": 1, "msg": "mismatched input ';'"},
        ]
        analysis = analyze_error_dependencies(raw_errors)
        self.assertEqual(analysis["total_errors"], 3)
        self.assertGreaterEqual(len(analysis["root_causes"]), 1)
        self.assertGreaterEqual(len(analysis["cascading_errors"]), 1)
        self.assertTrue(len(analysis["recommended_repair_order"]) == 3)


if __name__ == "__main__":
    unittest.main()

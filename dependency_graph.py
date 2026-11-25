"""
Multi-Error Dependency Graph & Cascade Analyzer
Analyzes relationships between multiple compiler errors to identify:
1. Root-cause errors (e.g. unclosed '{' or missing header)
2. Cascading / downstream phantom errors
3. Independent clusters that can be repaired in parallel batches
"""

from __future__ import annotations
from typing import List, Dict, Any, Set, Tuple


class ErrorNode:
    def __init__(self, error_id: str, line: int, col: int, reason: str, raw_msg: str):
        self.error_id = error_id
        self.line = line
        self.col = col
        self.reason = reason
        self.raw_msg = raw_msg
        self.is_root_cause = False
        self.cascade_dependents: List[str] = []
        self.cluster_id: int = 0


def analyze_error_dependencies(
    error_objects: List[Dict[str, Any]],
    source_code: str = "",
) -> Dict[str, Any]:
    """
    Constructs an error dependency graph from a list of compiler error objects.
    Clusters errors into independent repair groups and flags cascade sources.
    """
    if not error_objects:
        return {
            "total_errors": 0,
            "root_causes": [],
            "cascading_errors": [],
            "independent_clusters": [],
            "cascade_ratio": 0.0,
            "recommended_repair_order": [],
        }

    nodes: List[ErrorNode] = []
    for idx, err in enumerate(error_objects):
        line = err.get("line", 1)
        col = err.get("column", 1)
        msg = err.get("msg", "")
        # Reason extraction
        reason = "unknown"
        lower = msg.lower()
        if "';'" in lower:
            reason = "missing_semicolon"
        elif "'}'" in lower or "'{'" in lower:
            reason = "brace_mismatch"
        elif "')'" in lower or "'('" in lower:
            reason = "paren_mismatch"
        elif "extraneous" in lower:
            reason = "extraneous_token"
        elif "mismatched" in lower:
            reason = "mismatched_token"

        err_id = f"err_{idx+1}_L{line}"
        nodes.append(ErrorNode(err_id, line, col, reason, msg))

    # Sort nodes by line position
    nodes.sort(key=lambda n: (n.line, n.col))

    # Heuristic 1: Unclosed braces or missing headers cause subsequent errors on later lines
    root_cause_ids: Set[str] = set()
    cascading_ids: Set[str] = set()

    for i, node in enumerate(nodes):
        if node.reason == "brace_mismatch":
            node.is_root_cause = True
            root_cause_ids.add(node.error_id)
            # Flag errors on following lines in the same vicinity as likely cascades
            for j in range(i + 1, len(nodes)):
                downstream = nodes[j]
                if downstream.line > node.line and downstream.line <= node.line + 40:
                    downstream.is_root_cause = False
                    node.cascade_dependents.append(downstream.error_id)
                    cascading_ids.add(downstream.error_id)

    # If first error is early in file and multiple downstream errors exist, it has high root priority
    if nodes and nodes[0].error_id not in cascading_ids:
        nodes[0].is_root_cause = True
        root_cause_ids.add(nodes[0].error_id)

    # Heuristic 2: Cluster independent errors by line locality
    # Errors spaced more than 5 lines apart with no brace mismatch are independent
    cluster_counter = 1
    clusters: Dict[int, List[Dict[str, Any]]] = {}
    last_line = -999

    for node in nodes:
        if abs(node.line - last_line) > 5 and node.error_id not in cascading_ids:
            cluster_counter += 1
        node.cluster_id = cluster_counter
        last_line = node.line

        cluster_list = clusters.setdefault(node.cluster_id, [])
        cluster_list.append({
            "error_id": node.error_id,
            "line": node.line,
            "col": node.col,
            "reason": node.reason,
            "is_root_cause": node.is_root_cause,
        })

    # Prepare recommended repair order (root causes first, followed by independent errors)
    repair_order = []
    for node in nodes:
        if node.is_root_cause:
            repair_order.append(node.error_id)
    for node in nodes:
        if not node.is_root_cause and node.error_id not in cascading_ids:
            repair_order.append(node.error_id)
    for node in nodes:
        if node.error_id in cascading_ids and node.error_id not in repair_order:
            repair_order.append(node.error_id)

    cascade_ratio = round(len(cascading_ids) / len(nodes), 2) if nodes else 0.0

    return {
        "total_errors": len(nodes),
        "root_causes": list(root_cause_ids),
        "cascading_errors": list(cascading_ids),
        "independent_clusters": list(clusters.values()),
        "cascade_ratio": cascade_ratio,
        "recommended_repair_order": repair_order,
    }

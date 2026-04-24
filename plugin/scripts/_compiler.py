"""
Prompt Compiler — transforms a fathomed Intent Graph into a structured
markdown prompt for downstream Claude planning.

Concept ported from prior research (SSRN paper + MIT OSS at
github.com/ma-ziwei/fathom-mode); section structure, labels, instruction
header, and task-type directive strings follow ftg/compiler.py for
cross-version consistency.

Five-section output:
  [1] Task Anchor — original user request
  [2] User Expression & System Understanding — nodes grouped by raw_quote
  [3] User-Explicit Causal Relationships — only USER_EXPLICIT CAUSAL edges
  [4] Constraints & Conflicts — CONSTRAINT-type nodes + CONTRADICTION edges
  [5] System-Inferred Supplements — nodes without raw_quote anchor

Sections [3] / [4] / [5] are auto-omitted when empty. Keeps short sessions
concise.

Cut from ftg/compiler.py (intentionally not ported):
  - BIAS_CORRECTION_MAP / BIAS_LABELS
  - attachment_contexts rendering (no attachment handling in MVP)
  - dimension_states / dimension_assessment rendering
  - _render_coverage_summary
  - _render_chain / causal chain enumeration

Output is NOT a plan — it is a structured-intent prompt that Claude reads
AS planning input. The "plan" is what Claude produces by reasoning over
this output in the plan flow.
"""

from __future__ import annotations

from _graph import IntentGraph
from _models import EdgeSource, Node, NodeType, RelationType


MAX_EXPLICIT_CAUSAL_ITEMS = 6
MAX_CONSTRAINT_ITEMS = 8
MAX_ANCHORED_ITEMS_PER_QUOTE = 6
MAX_SYSTEM_INFERRED_ITEMS = 6


# Task-aware compilation directives — direct port from ftg/compiler.py
TASK_COMPILATION_DIRECTIVES: dict[str, str] = {
    "thinking": (
        "This is a thinking request. Present a structured analysis that "
        "addresses the user's stated concerns. Highlight trade-offs and "
        "hidden assumptions. Make a recommendation if the evidence supports "
        "one, but acknowledge uncertainty."
    ),
    "creation": (
        "This is a creation request. Produce the requested deliverable "
        "directly, respecting all stated constraints on purpose, audience, "
        "tone, and format. If key information is missing, note it but still "
        "produce a complete draft."
    ),
    "execution": (
        "This is an execution request. List the exact steps to perform. "
        "Flag any steps that could have significant or irreversible "
        "consequences. State what you will NOT do as clearly as what you "
        "will do. If prerequisites or permissions are unclear, ask before "
        "proceeding."
    ),
    "learning": (
        "This is a learning request. Provide a structured path tailored to "
        "the user's level and constraints. Be specific about resources and "
        "milestones. Match the depth and complexity to what the user can "
        "absorb."
    ),
}


COMPILER_INSTRUCTION_HEADER = (
    "The following is a structured intent analysis of the user's request, "
    "verified through multi-round dialogue. Use it to guide your response:\n"
    "\n"
    "- [1] Task Anchor: The user's original request — your response must address this.\n"
    "- [2] User Expression: Direct quotes and extracted understanding, grouped by the user's own words. "
    "Treat raw_quote lines as ground truth.\n"
    "- [3] User-Explicit Causal: Cause-effect relationships the user personally confirmed. "
    "Do NOT substitute correlation for these stated causes.\n"
    "- [4] Constraints & Conflicts: Hard constraints and internal tensions the user expressed. "
    "Address conflicts explicitly rather than ignoring them.\n"
    "- [5] System-Inferred: Supplementary understanding not directly quoted. "
    "Use cautiously; prefer [2] when they conflict.\n"
    "- Low confidence notes mean the system is uncertain about that interpretation. "
    "Acknowledge uncertainty rather than asserting confidently."
)


def compile_intent_graph(
    graph: IntentGraph,
    original_request: str,
    task_type: str = "general",
) -> str:
    """
    Compile an Intent Graph into a structured markdown prompt for
    downstream Claude planning.

    Sections [3] / [4] / [5] are auto-omitted when they would be empty
    — keeps output concise for short sessions.
    """
    sections: list[str] = [COMPILER_INSTRUCTION_HEADER]

    directive = TASK_COMPILATION_DIRECTIVES.get(task_type)
    if directive:
        sections.append(f"\nTask context: {directive}")

    sections.append("\n=== [1] Task Anchor ===")
    sections.append(f"Original user request: {original_request}")

    sections.append("\n=== [2] User Expression & System Understanding ===")
    sections.extend(_render_user_expression(graph))

    explicit_causal = _render_explicit_causal(graph)
    if explicit_causal:
        sections.append("\n=== [3] User-Explicit Causal Relationships ===")
        sections.extend(explicit_causal)

    constraints = _render_constraints(graph)
    if constraints:
        sections.append("\n=== [4] Constraints & Conflicts ===")
        sections.extend(constraints)

    inferred = _render_system_inferences(graph)
    if inferred:
        sections.append("\n=== [5] System-Inferred Supplements ===")
        sections.extend(inferred)

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_user_expression(graph: IntentGraph) -> list[str]:
    groups = _group_nodes_by_raw_quote(graph)
    if not groups:
        return ["No graph information that can be reliably anchored to the user's own words."]

    lines: list[str] = []
    for anchor_idx, group in enumerate(groups, start=1):
        quote = group["quote"]
        nodes = _dedupe_nodes_by_content(group["nodes"])

        lines.append(f"--- Anchor {anchor_idx} ---")
        lines.append(f"User: {quote}")

        visible = nodes[:MAX_ANCHORED_ITEMS_PER_QUOTE]
        for node in visible:
            lines.extend(_render_anchored_node(node))
        hidden = len(nodes) - len(visible)
        if hidden > 0:
            lines.append(f"- ({hidden} additional items from this anchor omitted)")
        lines.append("")

    if lines and not lines[-1].strip():
        lines.pop()
    return lines


def _render_anchored_node(node: Node) -> list[str]:
    lines = [f"- Understanding: {node.content}"]
    if node.confidence < 0.5:
        lines.append(
            f"  Low confidence: node confidence is {node.confidence:.0%} — "
            "retain uncertainty when using."
        )
    return lines


def _render_explicit_causal(graph: IntentGraph) -> list[str]:
    """List USER_EXPLICIT CAUSAL edges only (CFP discipline). Returns [] if none."""
    causal_edges = [
        e for e in graph.get_all_edges()
        if e.relation_type == RelationType.CAUSAL.value
        and e.source_type == EdgeSource.USER_EXPLICIT.value
    ]
    if not causal_edges:
        return []

    lines: list[str] = []
    for edge in causal_edges[:MAX_EXPLICIT_CAUSAL_ITEMS]:
        src = graph.get_node(edge.source)
        tgt = graph.get_node(edge.target)
        if src and tgt:
            lines.append(f"- {src.content} -> causes -> {tgt.content}")
    hidden = max(0, len(causal_edges) - MAX_EXPLICIT_CAUSAL_ITEMS)
    if hidden:
        lines.append(f"- ({hidden} additional user-explicit causal relationships omitted)")
    return lines


def _render_constraints(graph: IntentGraph) -> list[str]:
    constraints = _extract_constraints(graph)[:MAX_CONSTRAINT_ITEMS]
    if not constraints:
        return []
    return [f"- {item}" for item in constraints]


def _extract_constraints(graph: IntentGraph) -> list[str]:
    items: list[str] = []
    # CONSTRAINT-type nodes
    for node in graph.get_nodes_by_type(NodeType.CONSTRAINT.value):
        if node.content:
            items.append(node.content)

    # CONTRADICTION edges (only same-dim contradictions surface as conflicts,
    # mirroring ftg's filter that cross-dim contradictions are usually
    # structural not semantic)
    for src, tgt in graph.has_contradictions():
        src_node = graph.get_node(src)
        tgt_node = graph.get_node(tgt)
        if not src_node or not tgt_node:
            continue
        if src_node.dimension != tgt_node.dimension:
            continue
        items.append(
            f'Note: the following two items show tension or conflict: '
            f'"{_node_anchor_or_content(src_node)}" vs '
            f'"{_node_anchor_or_content(tgt_node)}".'
        )

    return _dedupe_preserve_order([item for item in items if item])


def _render_system_inferences(graph: IntentGraph) -> list[str]:
    """Nodes without raw_quote — system extracted these beyond the literal text."""
    unanchored = [n for n in graph.get_all_nodes() if not (n.raw_quote or "").strip()]
    nodes = _dedupe_nodes_by_content(unanchored)[:MAX_SYSTEM_INFERRED_ITEMS]
    if not nodes:
        return []

    lines: list[str] = []
    for node in nodes:
        lines.append(f"- {node.content}")
        if node.confidence < 0.5:
            lines.append(f"  Low confidence: node confidence is {node.confidence:.0%}.")
    hidden = max(0, len(unanchored) - len(nodes))
    if hidden:
        lines.append(f"- ({hidden} additional system-inferred supplements omitted)")
    return lines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _group_nodes_by_raw_quote(graph: IntentGraph) -> list[dict]:
    """Bucket nodes by their raw_quote (only nodes with non-empty raw_quote)."""
    groups: list[dict] = []
    index: dict[str, int] = {}
    for node in graph.get_all_nodes():
        quote = (node.raw_quote or "").strip()
        if not quote:
            continue
        if quote not in index:
            index[quote] = len(groups)
            groups.append({"quote": quote, "nodes": []})
        groups[index[quote]]["nodes"].append(node)
    return groups


def _node_anchor_or_content(node: Node) -> str:
    """Prefer raw_quote anchor when available, fall back to content[:80]."""
    quote = (node.raw_quote or "").strip()
    return quote if quote else node.content[:80]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _dedupe_nodes_by_content(nodes: list[Node]) -> list[Node]:
    seen: set[str] = set()
    result: list[Node] = []
    for node in nodes:
        key = node.content.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(node)
    return result

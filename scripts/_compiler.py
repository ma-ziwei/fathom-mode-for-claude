"""
Compile a Fathom session's state into a Structured Intent Summary.

Concept inspired by prior research (SSRN paper + prior library); no code copied.
Phase 1 scope: skeleton structure with crude dimension-bucketed grouping.
Phase 3 will replace internals with real raw_quote-based grouping + CFP causal
filtering + contradiction tensions, while keeping the same function signature.

The output is NOT a plan. It is a structured intent prompt that Claude reads
as planning input. The "plan" is what Claude produces by reasoning over this
input. User sees Claude's plan, not this output.
"""

from __future__ import annotations


_PLANNING_HINT_BY_TASK_TYPE = {
    "thinking":  "Plan the analysis approach.",
    "creation":  "Plan the artifact production steps.",
    "execution": "Plan the concrete operational actions.",
    "learning":  "Plan the learning sequence.",
    "general":   "Plan to fit the task as understood.",
}


def compile_intent_graph(state: dict, task: str | None = None, task_type: str | None = None) -> str:
    """
    Returns the Structured Intent Summary markdown for Claude to use as
    planning input.

    Phase 1 buckets nodes by primary dimension and renders 5 sections.
    Closes with a planning directive (NOT execution directive).

    Args:
        state: full state dict from active_session.json
        task:  override state["task"] if provided
        task_type: override state["task_type"] if provided

    Returns:
        Multi-line markdown string.
    """
    task = task or state.get("task", "<task not set>")
    task_type = task_type or state.get("task_type", "general")
    nodes = state.get("nodes", [])
    turn_count = state.get("turn_count", 0)
    score_pct = state.get("score_pct", 0)

    # Bucket nodes by primary dimension (Phase 3 will switch to raw_quote grouping).
    # CONSTRAINT-type nodes are excluded here — they appear ONLY in the dedicated
    # Constraints section below, regardless of their dimension. Avoids double-listing.
    by_dim: dict[str, list[dict]] = {}
    for node in nodes:
        if node.get("node_type") == "constraint":
            continue
        dim = node.get("dimension", "unknown")
        by_dim.setdefault(dim, []).append(node)

    sections: list[str] = []

    # --- Header ---
    sections.append("# Fathomed Intent")
    sections.append("")
    sections.append(f"**Task**: {task}")
    sections.append(f"**Task type**: {task_type}")
    sections.append(
        f"**Session depth**: {len(nodes)} node(s) across {len(by_dim)} dimension(s) "
        f"over {turn_count} turn(s); Fathom Score {score_pct}%"
    )
    sections.append("")

    # --- Section 1: Context (WHAT + WHO) ---
    sections.append("## Context")
    context_added = False
    for dim in ("what", "who"):
        for node in by_dim.get(dim, []):
            sections.append(f"- [{dim.upper()}] {node.get('content', '').strip()}")
            context_added = True
    if not context_added:
        sections.append("- (not yet captured in this session)")
    sections.append("")

    # --- Section 2: Motivation (WHY) ---
    sections.append("## Motivation")
    why_nodes = by_dim.get("why", [])
    if why_nodes:
        for node in why_nodes:
            sections.append(f"- {node.get('content', '').strip()}")
    else:
        sections.append("- (not yet captured)")
    sections.append("")

    # --- Section 3: Approach (HOW) ---
    sections.append("## Approach")
    how_nodes = by_dim.get("how", [])
    if how_nodes:
        for node in how_nodes:
            sections.append(f"- {node.get('content', '').strip()}")
    else:
        sections.append("- (not yet captured)")
    sections.append("")

    # --- Section 4: Constraints (CONSTRAINT-type, regardless of dimension) ---
    sections.append("## Constraints")
    constraint_nodes = [n for n in nodes if n.get("node_type") == "constraint"]
    if constraint_nodes:
        for node in constraint_nodes:
            sections.append(f"- {node.get('content', '').strip()}")
    else:
        sections.append("- (none identified)")
    sections.append("")

    # --- Section 5: Concrete Steps placeholder (Claude fills) ---
    sections.append("## Concrete Steps")
    sections.append("(Claude will draft these based on the above intent.)")
    sections.append("")

    # --- Planning directive ---
    hint = _PLANNING_HINT_BY_TASK_TYPE.get(task_type, _PLANNING_HINT_BY_TASK_TYPE["general"])
    sections.append("---")
    sections.append("**Planning directive**: Use this fathomed intent as your primary input "
                    "for planning and execution. Every element of your plan must be grounded "
                    "in a section above. Do not introduce concerns absent from the intent. "
                    "Do not omit constraints listed.")
    sections.append("")
    sections.append(f"*Task-type hint*: {hint}")

    return "\n".join(sections)

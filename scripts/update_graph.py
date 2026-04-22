#!/usr/bin/env python3
"""
Per-turn graph update + Score recomputation.

Day 2 reality: real Score formula via _scoring.compute_fathom_breakdown over
Claude-emitted nodes. Falls back to Day 1 stub behavior if --nodes is absent
(backward-compat during SKILL.md rollout).

CLI:
    update_graph.py --user-input "<verbatim user message>"
                    [--nodes '<JSON array of node dicts>']
                    [--task-type thinking|creation|execution|learning|general]

`session_id` is read from the state file, not from CLI (Lawrence's spec
adjustment from Day 1).

Day 3 will add: real IntentGraph operations (CFP edge downgrade, dedup).
Day 4 will add: causal marker detection wired into verified_causal_pairs.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from session_state import require_active, save_state
from _models import Node
from _scoring import compute_fathom_breakdown


# ---------------------------------------------------------------------------
# 6W cycle order — used by Day 1 stub fallback only.
# Day 3 swaps in real find_target_dimension(graph) from _dimensions.py.
# ---------------------------------------------------------------------------
_DIMENSION_CYCLE = ["what", "why", "how", "who", "when", "where"]
_ALL_DIMS = ["who", "what", "why", "when", "where", "how"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate_at_word_boundary(text: str, limit: int = 240) -> str:
    """
    Word-boundary truncation with ellipsis.
    Used only on stub-fallback content (when Claude doesn't emit --nodes).
    For Claude-emitted node content, store as-is — Claude controls length.
    """
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit)
    if cut < limit // 2:
        cut = limit
    return text[:cut].rstrip(",.;:") + "\u2026"


def _prefix_node_ids(nodes: list[Node], turn_count: int) -> list[Node]:
    """
    Prefix Claude-emitted ids with turn number to avoid collisions across turns.
    Claude emits 'n1', 'n2', etc. fresh each turn; we store as 't3_n1', 't3_n2'.
    Already-prefixed ids pass through unchanged (idempotent).
    """
    prefix = f"t{turn_count + 1}_"
    for node in nodes:
        if not node.id.startswith(prefix):
            node.id = prefix + node.id
    return nodes


def _stub_fallback_node(user_input: str, turn_count: int) -> Node:
    """Day 1 stub fallback: cycle dim, truncate content. Used when --nodes absent."""
    new_turn = turn_count + 1
    dim = _DIMENSION_CYCLE[(new_turn - 1) % len(_DIMENSION_CYCLE)]
    return Node(
        id=f"t{new_turn}_n{uuid.uuid4().hex[:6]}",
        content=_truncate_at_word_boundary(user_input, limit=240),
        raw_quote="",
        dimension=dim,
        node_type="fact",
        confidence=0.5,
    )


def _next_target_dimension(active_dims: list[str]) -> str:
    """Day 2 simple heuristic: first 6W dim not yet active. Day 3 swaps in real priority logic."""
    for dim in _ALL_DIMS:
        if dim not in active_dims:
            return dim
    return "why"  # all 6 covered → keep deepening WHY


def _parse_nodes_arg(nodes_arg: str | None, turn_count: int, warnings: list) -> list[Node]:
    """Parse --nodes JSON. On failure, log to warnings and return []."""
    if not nodes_arg:
        return []
    try:
        raw = json.loads(nodes_arg)
        if not isinstance(raw, list):
            warnings.append(f"--nodes must be a JSON array, got {type(raw).__name__}")
            return []
        nodes = [Node.from_dict(d) for d in raw]
        return _prefix_node_ids(nodes, turn_count)
    except json.JSONDecodeError as exc:
        warnings.append(f"--nodes JSON parse failed: {exc}")
        return []
    except (KeyError, TypeError) as exc:
        warnings.append(f"--nodes node missing required field: {exc}")
        return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Intent Graph after a user turn.")
    parser.add_argument("--user-input", required=True, help="The user's verbatim message.")
    parser.add_argument("--nodes", default=None, help="JSON array of Node dicts emitted by Claude.")
    parser.add_argument("--task-type", default=None,
                        choices=["thinking", "creation", "execution", "learning", "general"],
                        help="Optional task-type classification.")
    args = parser.parse_args()

    state = require_active()  # exits 1 if no active session

    user_input = args.user_input.strip()
    warnings = list(state.get("extraction_warnings", []))

    # Parse Claude's extraction (or fall back to stub)
    new_nodes = _parse_nodes_arg(args.nodes, state.get("turn_count", 0), warnings)
    if not new_nodes:
        # Stub fallback: backward-compat with Day 1 SKILL.md
        new_nodes = [_stub_fallback_node(user_input, state.get("turn_count", 0))]

    # Append nodes + dialogue, increment turn
    nodes_dicts = list(state.get("nodes", []))
    nodes_dicts.extend(node.to_dict() for node in new_nodes)

    dialogue = list(state.get("dialogue", []))
    dialogue.append({"role": "user", "content": user_input})

    new_turn = int(state.get("turn_count", 0)) + 1

    if args.task_type:
        state["task_type"] = args.task_type

    # Recompute real Score over all nodes ever extracted in this session
    all_nodes = [Node.from_dict(d) for d in nodes_dicts]
    verified_causal = state.get("verified_causal_pairs", {})  # Day 4 wires real pairs
    breakdown = compute_fathom_breakdown(all_nodes, verified_causal)

    new_score_pct = round(breakdown.fathom_score * 100)
    score_delta = new_score_pct - int(state.get("score_pct", 0))

    state.update({
        "turn_count": new_turn,
        "score_pct": new_score_pct,
        "score_breakdown": {
            "surface_pct": round(breakdown.surface_coverage * 100),
            "depth_pct": round(breakdown.depth_penetration * 100),
            "bedrock_pct": round(breakdown.bedrock_grounding * 100),
        },
        "nodes": nodes_dicts,
        "dialogue": dialogue,
        "extraction_warnings": warnings,
    })
    save_state(state)

    # Compute active dims + next target for the response JSON
    dims_active = sorted({n.dimension for n in all_nodes})
    next_target = _next_target_dimension(dims_active)

    summary_dims = ", ".join(d.upper() for d in dims_active) or "(none yet)"
    graph_summary = (
        f"{len(all_nodes)} node{'s' if len(all_nodes) != 1 else ''} across {summary_dims}. "
        "No causal edges yet (CFP wires Day 4)."
    )

    sys.stdout.write(json.dumps({
        "score_pct": new_score_pct,
        "score_delta": score_delta,
        "surface_pct": state["score_breakdown"]["surface_pct"],
        "depth_pct": state["score_breakdown"]["depth_pct"],
        "bedrock_pct": state["score_breakdown"]["bedrock_pct"],
        "dimensions_active": dims_active,
        "next_target_dimension": next_target,
        "turn_count": new_turn,
        "graph_summary": graph_summary,
        "task_type": state.get("task_type", "general"),
        "extraction_warnings": warnings,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

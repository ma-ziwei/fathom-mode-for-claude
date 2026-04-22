#!/usr/bin/env python3
"""
Initialize a new Fathom Mode session.

Day 2 reality: if Claude emits first-turn nodes via --nodes, compute real
initial Score via _scoring; else fall back to Day 1 stub formula.

CLI:
    init_session.py --task "<user task>"
                    [--nodes '<JSON array of Node dicts>']
                    [--task-type thinking|creation|execution|learning|general]

The /fathom-mode:fathom slash command body currently passes only --task.
The --nodes accept is forward-compat for Day 3+ when commands/fathom.md may
add first-turn extraction. Day 2 turn 0 always lands on the stub fallback;
turn 1+ uses real Score via update_graph.py per SKILL.md guidance.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

from session_state import save_state
from _models import Node
from _scoring import compute_fathom_breakdown


_ALL_DIMS = ["who", "what", "why", "when", "where", "how"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _initial_score_pct_stub(task: str) -> int:
    """
    Day 1 stub fallback: longer initial task descriptions imply more dimensions
    are pre-filled, so initial score is higher. Floor 35%, cap 55% per
    plan verification range. Used when Claude doesn't emit --nodes.
    """
    base = len(task.strip())
    return min(55, max(35, base // 4))


def _parse_initial_nodes(nodes_arg: str | None, warnings: list) -> list[Node]:
    """Parse --nodes JSON. On failure, log to warnings and return []."""
    if not nodes_arg:
        return []
    try:
        raw = json.loads(nodes_arg)
        if not isinstance(raw, list):
            warnings.append(f"--nodes must be a JSON array, got {type(raw).__name__}")
            return []
        nodes = [Node.from_dict(d) for d in raw]
        # Prefix initial-turn nodes with t0_ — they come from the TASK
        # framing, before any user reply. update_graph.py uses t1_, t2_, ...
        # for subsequent turns (1-indexed by user-reply count).
        for node in nodes:
            if not node.id.startswith("t0_"):
                node.id = f"t0_{node.id}"
        return nodes
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
    parser = argparse.ArgumentParser(description="Initialize a Fathom Mode session.")
    parser.add_argument("--task", required=True, help="The user's task description.")
    parser.add_argument("--nodes", default=None, help="Optional initial extraction JSON.")
    parser.add_argument("--task-type", default=None,
                        choices=["thinking", "creation", "execution", "learning", "general"],
                        help="Optional task-type classification.")
    args = parser.parse_args()

    task = args.task.strip()
    if not task:
        sys.stdout.write(json.dumps({
            "error": "empty_task",
            "message": "A non-empty task description is required.",
        }))
        sys.exit(1)

    session_id = uuid.uuid4().hex[:12]
    now_iso = datetime.now(timezone.utc).isoformat()
    warnings: list = []

    # Build the fresh state with all Day 2 fields (additive over Day 1)
    state = {
        "session_id": session_id,
        "task": task,
        "started_at": now_iso,
        "task_type": args.task_type or "general",
        "turn_count": 0,
        "score_pct": 0,
        "score_breakdown": {"surface_pct": 0, "depth_pct": 0, "bedrock_pct": 0},
        "nodes": [],
        "edges": [],
        "dialogue": [],
        "verified_causal_pairs": {},  # Forward-compat: Day 4 wires real causal pairs
        "extraction_warnings": [],
    }

    # First-turn extraction (forward-compat path)
    initial_nodes = _parse_initial_nodes(args.nodes, warnings)

    if initial_nodes:
        # Real path: compute Score from Claude's extraction
        state["nodes"] = [n.to_dict() for n in initial_nodes]
        breakdown = compute_fathom_breakdown(initial_nodes, {})
        state["score_pct"] = round(breakdown.fathom_score * 100)
        state["score_breakdown"] = {
            "surface_pct": round(breakdown.surface_coverage * 100),
            "depth_pct": round(breakdown.depth_penetration * 100),
            "bedrock_pct": round(breakdown.bedrock_grounding * 100),
        }
    else:
        # Day 1 stub fallback (current /fathom command body lands here every time)
        stub_pct = _initial_score_pct_stub(task)
        state["score_pct"] = stub_pct
        state["score_breakdown"] = {
            "surface_pct": stub_pct,
            "depth_pct": max(0, stub_pct - 20),
            "bedrock_pct": 0,
        }

    state["extraction_warnings"] = warnings
    save_state(state)

    dims_active = sorted({n.dimension for n in initial_nodes})
    next_target = next((d for d in _ALL_DIMS if d not in dims_active), "why")

    sys.stdout.write(json.dumps({
        "session_id": session_id,
        "task": task,
        "task_type": state["task_type"],
        "score_pct": state["score_pct"],
        "score_delta": state["score_pct"],
        "surface_pct": state["score_breakdown"]["surface_pct"],
        "depth_pct": state["score_breakdown"]["depth_pct"],
        "bedrock_pct": state["score_breakdown"]["bedrock_pct"],
        "dimensions_active": dims_active,
        "next_target_dimension": next_target,
        "turn_count": 0,
        "graph_summary": (
            f"New session. {len(initial_nodes)} node{'s' if len(initial_nodes) != 1 else ''} "
            "from first-turn extraction." if initial_nodes
            else "New session. No nodes yet — first user message will populate."
        ),
        "extraction_warnings": warnings,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Initialize a new Fathom Mode session.

When Claude emits first-turn nodes via --nodes, build a real IntentGraph
and compute the initial Score over its nodes. When --nodes is absent
(the path the hook actually takes today), state initializes with
score_pct=0 — turn 1 (update_graph.py) computes the real Score from
Claude's first-turn extraction. Persisting a non-zero baseline here
would corrupt the turn-1 delta (update_graph.py would compute it as
real_score - stub_baseline, producing artificially small or negative
deltas on the user's first message).

CLI:
    init_session.py --task "<user task>"
                    [--nodes '<JSON array of Node dicts>']
                    [--task-type thinking|creation|execution|learning|general]

Stdin payload (preferred when available — bypasses shell escaping):
    init_session.py <<'FATHOM_INIT_END'
    {"task": "...", "nodes": [...], "task_type": "..."}
    FATHOM_INIT_END

Output JSON includes a pre-rendered `score_block_str` so the caller
(SKILL.md instructs Claude here) can use it verbatim — no LLM-side
rendering drift.
"""

from __future__ import annotations

import argparse
import json
import select
import sys
import uuid
from datetime import datetime, timezone

from session_state import save_state
from _models import Node
from _scoring import compute_fathom_breakdown
from _graph import IntentGraph
from _dimensions import find_target_dimension
from update_graph import render_score_block  # shared 2-line bar renderer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    # --task is no longer required at argparse level; a stdin JSON payload
    # may supply it instead. Validation happens after both sources are read.
    parser.add_argument("--task", default=None, help="The user's task description.")
    parser.add_argument("--nodes", default=None, help="Optional initial extraction JSON.")
    parser.add_argument("--task-type", default=None,
                        choices=["thinking", "creation", "execution", "learning", "general"],
                        help="Optional task-type classification.")
    args = parser.parse_args()

    # Optional stdin JSON payload (preferred path; overrides args). Mirrors
    # update_graph.py: SKILL.md / start.md instruct Claude to invoke this
    # script via Bash heredoc with quoted delimiter (<<'FATHOM_INIT_END')
    # so apostrophes / em-dashes / dollar signs in the task pass through
    # literally, no shell escaping required. Read raw bytes and decode as
    # UTF-8 explicitly so the OS default codec (GBK / cp1252 on Windows)
    # cannot mangle non-ASCII task text.
    stdin_payload = None
    if not sys.stdin.isatty():
        # Probe stdin before blocking read: Cowork's bash tool may leave
        # stdin as an open-but-empty pipe that never closes — sys.stdin.
        # buffer.read() would block until Cowork's 45s RPC timeout. If no
        # data is ready within the probe window, proceed with CLI args only.
        try:
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            has_data = bool(ready)
        except (OSError, ValueError):
            has_data = True  # Non-Unix fallback (select on fd unsupported)
        if has_data:
            try:
                raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
                if raw.strip():
                    stdin_payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                sys.stdout.write(json.dumps({
                    "error": "stdin_parse_failed",
                    "message": f"stdin payload JSON parse failed: {exc}",
                }))
                sys.exit(1)

    task = args.task
    nodes_json = args.nodes
    task_type = args.task_type
    if isinstance(stdin_payload, dict):
        task = stdin_payload.get("task", task)
        if "nodes" in stdin_payload:
            nodes_json = json.dumps(stdin_payload["nodes"])
        task_type = stdin_payload.get("task_type", task_type)

    task = (task or "").strip()
    if not task:
        sys.stdout.write(json.dumps({
            "error": "empty_task",
            "message": (
                "A non-empty task description is required "
                "(via --task arg or stdin JSON payload)."
            ),
        }))
        sys.exit(1)

    session_id = uuid.uuid4().hex[:12]
    now_iso = datetime.now(timezone.utc).isoformat()
    warnings: list = []

    # Build the fresh state with all current fields
    state = {
        "session_id": session_id,
        "task": task,
        "started_at": now_iso,
        "task_type": task_type or "general",
        "turn_count": 0,
        "score_pct": 0,
        "score_breakdown": {"surface_pct": 0, "depth_pct": 0, "bedrock_pct": 0},
        "nodes": [],
        "edges": [],
        "dialogue": [],
        "verified_causal_pairs": {},
        "extraction_warnings": [],
    }

    initial_nodes = _parse_initial_nodes(nodes_json, warnings)

    # Build the graph (empty if no initial_nodes; populated otherwise).
    # Same graph used for Score computation AND next-target dimension
    # selection so init_session is consistent with update_graph.
    graph = IntentGraph()
    for n in initial_nodes:
        graph.add_node(n)

    if initial_nodes:
        # Real path: compute Score from Claude's first-turn extraction
        breakdown = compute_fathom_breakdown(graph.get_all_nodes(), {})
        state["nodes"] = [n.to_dict() for n in graph.get_all_nodes()]
        state["score_pct"] = round(breakdown.fathom_score * 100)
        state["score_breakdown"] = {
            "surface_pct": round(breakdown.surface_coverage * 100),
            "depth_pct": round(breakdown.depth_penetration * 100),
            "bedrock_pct": round(breakdown.bedrock_grounding * 100),
        }
    # else: state keeps score_pct=0 + zeroed breakdown from initial setup.
    # Persisting a non-zero stub baseline here would corrupt the turn-1
    # delta (update_graph.py would compute it as real_score - baseline,
    # producing artificially small or negative deltas on turn 1).

    state["extraction_warnings"] = warnings
    save_state(state)

    dims_active = sorted({n.dimension for n in initial_nodes if n.dimension})
    next_target = find_target_dimension(graph)

    score_block_str = render_score_block(state["score_pct"], state["score_pct"])

    sys.stdout.write(json.dumps({
        "session_id": session_id,
        "task": task,
        "task_type": state["task_type"],
        "score_pct": state["score_pct"],
        "score_delta": state["score_pct"],  # turn 0 — delta is the full score
        "score_block_str": score_block_str,
        "surface_pct": state["score_breakdown"]["surface_pct"],
        "depth_pct": state["score_breakdown"]["depth_pct"],
        "bedrock_pct": state["score_breakdown"]["bedrock_pct"],
        "dimensions_active": dims_active,
        "next_target_dimension": next_target,
        "turn_count": 0,
        "graph_summary": (
            f"New session. {len(initial_nodes)} node"
            f"{'s' if len(initial_nodes) != 1 else ''} from first-turn extraction."
            if initial_nodes
            else "New session. No nodes yet — first user message will populate."
        ),
        "extraction_warnings": warnings,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

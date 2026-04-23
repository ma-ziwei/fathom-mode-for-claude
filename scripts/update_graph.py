#!/usr/bin/env python3
"""
Per-turn graph update + Score recomputation.

Phase 2+3 reality: full Intent Graph operations via _graph.IntentGraph
(CFP downgrade enforced at add_edge), causal marker detection on user
input via _causal (USER_EXPLICIT CAUSAL edges only), real next-target
dimension via _dimensions.find_target_dimension. Score still computed
by _scoring.compute_fathom_breakdown over the graph's node list.

CLI:
    update_graph.py --user-input "<verbatim user message>"
                    [--nodes '<JSON array of node dicts>']
                    [--task-type thinking|creation|execution|learning|general]

Defensive arg aliases (silently accepted for LLM hallucination cases):
    --user-message  alias for --user-input
    --turn / --turn-count / --session-id  silently ignored

Output JSON now includes a pre-rendered `score_block_str` (2-line
`Fathom Score\\n{bar} {pct}% ({+|-}delta)`) for downstream callers
to use verbatim — eliminates LLM rendering drift.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from session_state import require_active, save_state
from _models import Edge, Node
from _scoring import compute_fathom_breakdown
from _graph import IntentGraph
from _dimensions import find_target_dimension
from _causal import detect_causal_markers, match_markers_to_nodes


# Day 1 stub fallback cycle — used only when --nodes is absent
_DIMENSION_CYCLE = ["what", "why", "how", "who", "when", "where"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _truncate_at_word_boundary(text: str, limit: int = 240) -> str:
    """Word-boundary truncation with ellipsis. Used only on stub-fallback content."""
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
    Claude emits 'n1', 'n2' fresh each turn; we store as 't3_n1', 't3_n2'.
    Already-prefixed ids pass through unchanged (idempotent).
    """
    prefix = f"t{turn_count + 1}_"
    for node in nodes:
        if not node.id.startswith(prefix):
            node.id = prefix + node.id
    return nodes


def _stub_fallback_node(user_input: str, turn_count: int) -> Node:
    """Day 1 stub fallback — used when Claude doesn't pass --nodes."""
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


def render_score_block(score_pct: int, score_delta: int) -> str:
    """
    Pre-render the 2-line Score block. Output format:

        Fathom Score
        ██████░░░░░░░░ NN% (+N)

    Top bar is exactly 14 chars (`█` filled, `░` empty). The delta is
    always shown with explicit sign (+5 / -3 / +0).

    SKILL.md instructs Claude to use this string verbatim — no
    self-rendering, no embellishment, no symbol substitution. Pre-rendering
    here eliminates the LLM-side drift we observed earlier (Claude
    swapping `█/░` for `▓/░`, condensing 3 sub-rows to 1, adding `━`
    decoration, etc.).
    """
    pct = max(0, min(100, int(score_pct)))
    bar_fill = round(pct / 100 * 14)
    bar_fill = max(0, min(14, bar_fill))
    bar = "\u2588" * bar_fill + "\u2591" * (14 - bar_fill)
    sign = "+" if score_delta >= 0 else ""
    return f"Fathom Score\n{bar} {pct}% ({sign}{score_delta})"


# Plan-readiness threshold + hint string. Single source of truth: the
# 50% threshold lives in this one helper, NOT in the hook (hook used to
# do `if state.score_pct >= 50` dispatch but that produced a one-turn
# lag because hook fires pre-update_graph; now the judgment lives next
# to the production of the score, eliminating the lag).
PLAN_READY_THRESHOLD = 50
PLAN_HINT_TEXT = (
    "💡 Ready to plan? Reply **plan** to draft your plan from this session."
)


def render_plan_hint(score_pct: int) -> str:
    """
    Return the plan-hint string when score has crossed the threshold,
    else empty string. Hook reminder instructs Claude to append this
    string verbatim at the end of the response if non-empty — no LLM
    threshold judgment needed.
    """
    return PLAN_HINT_TEXT if int(score_pct) >= PLAN_READY_THRESHOLD else ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Intent Graph after a user turn.")
    # Accept --user-message as a defensive alias — Claude has been observed
    # hallucinating that flag name (semantically plausible) on first try.
    parser.add_argument(
        "--user-input", "--user-message",
        dest="user_input", default=None,
        help="The user's verbatim message. (--user-message accepted as alias. "
             "Optional if a JSON payload is piped to stdin.)",
    )
    parser.add_argument("--nodes", default=None, help="JSON array of Node dicts emitted by Claude.")
    parser.add_argument("--task-type", default=None,
                        choices=["thinking", "creation", "execution", "learning", "general"],
                        help="Optional task-type classification.")
    # Defensive: silently accept --turn / --turn-count / --session-id flags
    # that Claude has been observed hallucinating. Script tracks these
    # internally from the state file; passed values are ignored.
    parser.add_argument("--turn", "--turn-count", dest="_ignored_turn",
                        default=None, help=argparse.SUPPRESS)
    parser.add_argument("--session-id", dest="_ignored_session_id",
                        default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    # --- Optional stdin JSON payload (preferred path; overrides args) ---
    # The hook reminder instructs Claude to invoke this script via a Bash
    # heredoc with quoted delimiter (<<'FATHOM_TURN_END'), routing all
    # user-derived text through stdin as a JSON object. This bypasses shell
    # quoting entirely - apostrophes / em-dashes / dollar signs in the
    # user's message no longer require escaping. CLI args remain supported
    # for standalone debugging and --help discoverability.
    stdin_payload = None
    if not sys.stdin.isatty():
        try:
            raw = sys.stdin.read()
            if raw.strip():
                stdin_payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"stdin payload JSON parse failed: {exc}", file=sys.stderr)
            sys.exit(1)

    user_input = args.user_input
    nodes_json = args.nodes
    task_type = args.task_type
    if isinstance(stdin_payload, dict):
        user_input = stdin_payload.get("user_input", user_input)
        if "nodes" in stdin_payload:
            nodes_json = json.dumps(stdin_payload["nodes"])
        task_type = stdin_payload.get("task_type", task_type)

    if not user_input:
        parser.error(
            'user_input is required (via stdin JSON payload {"user_input": ...} '
            'or --user-input arg)'
        )

    state = require_active()  # exits 1 if no active session

    user_input = user_input.strip()
    # Defense: replace any lone UTF-16 surrogates (e.g., \ud83d without a
    # paired low surrogate) with `?`. The encode/decode round-trip with
    # errors='replace' substitutes only the unencodable chars and leaves
    # valid Unicode intact. Sources: Claude's JSON payload may contain
    # \uXXXX escapes that split a surrogate pair; user paste may include
    # mojibake. session_state.save_state has a storage-layer guard
    # (ensure_ascii=True), this is the entry-layer complement keeping
    # in-memory state and downstream extraction inputs clean.
    user_input = user_input.encode('utf-8', errors='replace').decode('utf-8')
    warnings = list(state.get("extraction_warnings", []))

    # --- Reconstruct the graph from persisted state ---
    graph = IntentGraph()
    for nd in state.get("nodes", []):
        graph.add_node(Node.from_dict(nd))
    for ed in state.get("edges", []):
        graph.add_edge(Edge.from_dict(ed))

    # --- Parse Claude's extraction (or fall back to Day 1 stub) ---
    new_nodes = _parse_nodes_arg(nodes_json, state.get("turn_count", 0), warnings)
    if not new_nodes:
        new_nodes = [_stub_fallback_node(user_input, state.get("turn_count", 0))]

    for n in new_nodes:
        graph.add_node(n)

    # --- Causal marker detection on user input → USER_EXPLICIT CAUSAL edges ---
    detections = detect_causal_markers(user_input)
    purpose_markers = [d for d in detections if d["type"] == "purpose"]
    causal_edges = match_markers_to_nodes(detections, graph.get_all_nodes())
    for e in causal_edges:
        graph.add_edge(e)  # CFP downgrade enforced inside add_edge

    # Log purpose markers separately (CFP discipline: never edged)
    if purpose_markers:
        existing_purpose_log = list(state.get("purpose_markers_log", []))
        existing_purpose_log.extend(purpose_markers)
        state["purpose_markers_log"] = existing_purpose_log

    # --- Score over the updated graph ---
    verified_causal = state.get("verified_causal_pairs", {})  # later wires real verified pairs
    breakdown = compute_fathom_breakdown(graph.get_all_nodes(), verified_causal)
    new_score_pct = round(breakdown.fathom_score * 100)
    score_delta = new_score_pct - int(state.get("score_pct", 0))

    # --- Persist updated state ---
    new_turn = int(state.get("turn_count", 0)) + 1
    dialogue = list(state.get("dialogue", []))
    dialogue.append({"role": "user", "content": user_input})

    if task_type:
        state["task_type"] = task_type

    state.update({
        "turn_count": new_turn,
        "score_pct": new_score_pct,
        "score_breakdown": {
            "surface_pct": round(breakdown.surface_coverage * 100),
            "depth_pct": round(breakdown.depth_penetration * 100),
            "bedrock_pct": round(breakdown.bedrock_grounding * 100),
        },
        "nodes": [n.to_dict() for n in graph.get_all_nodes()],
        "edges": [e.to_dict() for e in graph.get_all_edges()],
        "dialogue": dialogue,
        "extraction_warnings": warnings,
    })
    save_state(state)

    # --- Compute next-target + summary for the response JSON ---
    next_target = find_target_dimension(graph)
    dims_active = sorted({n.dimension for n in graph.get_all_nodes() if n.dimension})

    summary_dims = ", ".join(d.upper() for d in dims_active) or "(none yet)"
    edge_count = graph.edge_count()
    causal_count = sum(
        1 for e in graph.get_all_edges()
        if e.relation_type == "causal"
    )
    graph_summary = (
        f"{graph.node_count()} node{'s' if graph.node_count() != 1 else ''}, "
        f"{edge_count} edge{'s' if edge_count != 1 else ''} "
        f"({causal_count} user-explicit causal) across {summary_dims}."
    )

    score_block_str = render_score_block(new_score_pct, score_delta)
    plan_hint_str = render_plan_hint(new_score_pct)

    sys.stdout.write(json.dumps({
        "score_pct": new_score_pct,
        "score_delta": score_delta,
        "score_block_str": score_block_str,
        "plan_hint_str": plan_hint_str,
        "surface_pct": state["score_breakdown"]["surface_pct"],
        "depth_pct": state["score_breakdown"]["depth_pct"],
        "bedrock_pct": state["score_breakdown"]["bedrock_pct"],
        "dimensions_active": dims_active,
        "next_target_dimension": next_target,
        "turn_count": new_turn,
        "graph_summary": graph_summary,
        "task_type": state.get("task_type", "general"),
        "extraction_warnings": warnings,
        "causal_edges_added": len(causal_edges),
        "purpose_markers_logged": len(purpose_markers),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
compile_plan.py — Print the Structured Intent for the active session
AND advance the session FSM into AWAITING_APPROVAL state.

Builds an IntentGraph from persisted state, then calls
_compiler.compile_intent_graph(graph, original_request, task_type) to
render the 5-section structured-intent markdown. Output is what Claude
reads as planning input (NOT shown to the user verbatim — see
commands/fathom-plan.md for the contract).

State machine: this script is the SINGLE convergence point for both
plan-drafting entry paths (conversational "plan" trigger from the
hook's IN_SESSION reminder + explicit /fathom-mode:fathom-plan slash
command). On invocation it sets state["awaiting_approval"] = True
BEFORE rendering, so the FSM correctly transitions even if rendering
fails partway. The next-turn hook dispatch reads the flag and routes
to the AWAITING_APPROVAL reminder.
"""

from __future__ import annotations

import sys

from session_state import require_active, save_state
from _models import Edge, Node
from _graph import IntentGraph
from _compiler import compile_intent_graph


def main() -> None:
    state = require_active()  # exits 1 with error JSON if no active session

    # STATE TRANSITION: enter AWAITING_APPROVAL.
    # Write before rendering so the FSM transitions even on render failure.
    state["awaiting_approval"] = True
    save_state(state)

    # Reconstruct graph from persisted state
    graph = IntentGraph()
    for nd in state.get("nodes", []):
        graph.add_node(Node.from_dict(nd))
    for ed in state.get("edges", []):
        graph.add_edge(Edge.from_dict(ed))

    output = compile_intent_graph(
        graph,
        original_request=state.get("task", "(task not set)"),
        task_type=state.get("task_type", "general"),
    )
    sys.stdout.write(output)


if __name__ == "__main__":
    main()

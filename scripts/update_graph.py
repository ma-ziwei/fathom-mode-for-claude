#!/usr/bin/env python3
"""
Day 1 stub: per-turn graph update + score recomputation.

Real algorithm lands Day 2-3. For now this script:
  - increments turn_count
  - appends one fake node per turn, cycling dimension through WHAT/WHY/HOW/WHO
  - applies a diminishing-returns score curve approximating the real
    1 - exp(-k * latent_depth) shape (real formula in investigation report A.4)
  - returns the JSON contract that SKILL.md expects

`session_id` is read from the state file, not a CLI arg, per Lawrence's spec
adjustment (one less parameter for Claude to track per turn).
"""

from __future__ import annotations

import argparse
import json
import sys

from session_state import require_active, save_state


# Cycle dimensions in order of fathom-priority (HOW > WHY > WHO > WHAT > WHEN > WHERE).
# Day 1 picks them deterministically; Day 2 will pick based on real graph state.
_DIMENSION_CYCLE = ["what", "why", "how", "who", "when", "where"]


def _stub_score_step(current: int) -> tuple[int, int]:
    """
    Approximate the diminishing-returns shape of the real Score curve.
    gain shrinks as current rises; never crosses 85% via stub.
    Returns (new_score, gain).
    """
    if current >= 85:
        return current, 0
    gain = max(3, int((85 - current) * 0.35))
    return current + gain, gain


def _next_target_dimension(active: list[str]) -> str:
    """Pick the next dimension to ask about: first one not yet active."""
    for dim in _DIMENSION_CYCLE:
        if dim not in active:
            return dim
    return _DIMENSION_CYCLE[0]


def _truncate_at_word_boundary(text: str, limit: int = 240) -> str:
    """
    Word-boundary truncation with ellipsis.

    If text fits in `limit`, return as-is.
    Else: cut at the last whitespace at-or-before `limit`. If no whitespace
    found in the first half (limit // 2), fall back to hard-cut at `limit`
    (defensive — handles pathological no-space inputs).
    """
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text.rfind(" ", 0, limit)
    if cut < limit // 2:
        cut = limit
    return text[:cut].rstrip(",.;:") + "\u2026"


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Intent Graph after a user turn.")
    parser.add_argument("--user-input", required=True, help="The user's verbatim message.")
    args = parser.parse_args()

    state = require_active()  # exits 1 if no active session

    user_input = args.user_input.strip()

    # Increment turn, append fake node, recompute score.
    new_turn = int(state.get("turn_count", 0)) + 1
    new_dim = _DIMENSION_CYCLE[(new_turn - 1) % len(_DIMENSION_CYCLE)]
    new_node = {
        "id": f"n{new_turn}",
        "dimension": new_dim,
        "content": _truncate_at_word_boundary(user_input, limit=240),
    }

    nodes = list(state.get("nodes", []))
    nodes.append(new_node)

    current_score = int(state.get("score_pct", 0))
    new_score, score_delta = _stub_score_step(current_score)

    dialogue = list(state.get("dialogue", []))
    dialogue.append({"role": "user", "content": user_input})

    active_dims = sorted({n["dimension"] for n in nodes})
    next_target = _next_target_dimension(active_dims)

    state.update({
        "turn_count": new_turn,
        "score_pct": new_score,
        "nodes": nodes,
        "dialogue": dialogue,
    })
    save_state(state)

    summary_dims = ", ".join(d.upper() for d in active_dims) or "(none yet)"
    graph_summary = (
        f"{len(nodes)} node{'s' if len(nodes) != 1 else ''} across {summary_dims}. "
        "No causal edges yet (CFP requires user-explicit causal language — Day 4 wires this)."
    )

    sys.stdout.write(json.dumps({
        "score_pct": new_score,
        "score_delta": score_delta,
        "dimensions_active": active_dims,
        "next_target_dimension": next_target,
        "turn_count": new_turn,
        "graph_summary": graph_summary,
    }))


if __name__ == "__main__":
    main()

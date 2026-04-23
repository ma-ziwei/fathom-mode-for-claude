#!/usr/bin/env python3
"""
Render the active Fathom session as user-facing markdown.

Output goes to stdout; the /fathom:status command presents it verbatim.
Day 1: bar chart + dimension counts + brief dialogue summary.
Day 2+: richer graph rendering once real edges/causal relationships exist.
"""

from __future__ import annotations

import sys

from session_state import require_active


_BAR_WIDTH = 14
_ALL_DIMENSIONS = ["what", "why", "how", "who", "when", "where"]


def _bar(score_pct: int) -> str:
    filled = int(round(_BAR_WIDTH * score_pct / 100))
    filled = max(0, min(_BAR_WIDTH, filled))
    return "█" * filled + "░" * (_BAR_WIDTH - filled)


def _dimension_counts(nodes: list[dict]) -> dict[str, int]:
    counts = {dim: 0 for dim in _ALL_DIMENSIONS}
    for n in nodes:
        dim = n.get("dimension", "")
        if dim in counts:
            counts[dim] += 1
    return counts


def _expected_turns(turn_count: int) -> str:
    """Rough estimate of how many turns to be plan-ready — for orientation only."""
    if turn_count <= 3:
        return "~6-8 expected"
    if turn_count <= 6:
        return "~8-10 expected"
    return "plan-ready depth"


def main() -> None:
    state = require_active()

    task = state.get("task", "(unknown task)")
    turn = int(state.get("turn_count", 0))
    score = int(state.get("score_pct", 0))
    nodes = state.get("nodes", [])
    dialogue = state.get("dialogue", [])

    counts = _dimension_counts(nodes)
    next_dim = next((d for d in _ALL_DIMENSIONS if counts[d] == 0), _ALL_DIMENSIONS[0])

    lines: list[str] = []
    lines.append("## Fathom Session Status")
    lines.append("")
    lines.append(f"**Task**: {task}")
    lines.append(f"**Turn**: {turn} of {_expected_turns(turn)}")
    lines.append(f"**Fathom Score**: `{_bar(score)} {score}%` (asymptotic to 100, never reaches)")
    lines.append("")
    lines.append("### Active Dimensions")
    for dim in _ALL_DIMENSIONS:
        c = counts[dim]
        if c > 0:
            lines.append(f"- {dim.upper()}: {c} node{'s' if c != 1 else ''}")
        elif dim == next_dim:
            lines.append(f"- {dim.upper()}: (empty — next question target)")
        else:
            lines.append(f"- {dim.upper()}: (empty)")
    lines.append("")
    lines.append("### Dialogue Summary")
    if not dialogue:
        lines.append("_No user turns yet — first message will populate the graph._")
    else:
        for i, turn_entry in enumerate(dialogue, start=1):
            content = (turn_entry.get("content") or "").strip()
            preview = content[:80] + ("…" if len(content) > 80 else "")
            lines.append(f"{i}. {preview}")
    lines.append("")
    lines.append("_Commands: `/fathom:plan` to plan · `/fathom:exit` to leave_")
    lines.append("")

    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()

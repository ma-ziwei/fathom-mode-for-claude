#!/usr/bin/env python3
"""
Day 1 stub: render a 5-section structured plan with placeholder content
derived from the active session's task and node list.

Real Compiler lands Day 4. The output structure is defined in
references/compile-format.md and MUST be preserved across versions so
SKILL.md / fathom-compile command behavior stays stable.
"""

from __future__ import annotations

import sys

from session_state import require_active


_DIMENSION_LABELS = {
    "who": "WHO — people involved, affected, or whose judgment matters",
    "what": "WHAT — the concrete subject or deliverable",
    "why": "WHY — the underlying motivation or goal",
    "how": "HOW — methods, constraints, criteria",
    "when": "WHEN — timeline, deadline, sequencing",
    "where": "WHERE — location, context, setting",
}

_DIMENSION_ORDER = ["who", "what", "why", "how", "when", "where"]


def _intent_summary(task: str, turn_count: int) -> str:
    """Stub: paraphrase the task, acknowledging the dialogue depth."""
    return (
        f"Across {turn_count} turn{'s' if turn_count != 1 else ''} of dialogue, "
        f"the user is working on: {task}. "
        "Day 4 will replace this paragraph with a real distillation drawn from the highest-confidence "
        "INTENT and GOAL nodes in the Intent Graph; for the Day 1 skeleton this is a faithful echo "
        "of the original task."
    )


def _structured_context(nodes: list[dict]) -> list[str]:
    """Group nodes by dimension and render bulleted sections."""
    by_dim: dict[str, list[str]] = {dim: [] for dim in _DIMENSION_ORDER}
    for n in nodes:
        dim = n.get("dimension", "")
        content = (n.get("content") or "").strip()
        if dim in by_dim and content:
            by_dim[dim].append(content)

    lines: list[str] = []
    any_section = False
    for dim in _DIMENSION_ORDER:
        items = by_dim[dim]
        if not items:
            continue
        any_section = True
        lines.append(f"**{_DIMENSION_LABELS[dim]}**")
        for item in items[:6]:
            lines.append(f"- {item}")
        lines.append("")

    if not any_section:
        lines.append("_No dimensions populated yet — the graph is empty. "
                     "(For a real session, first user turn produces the first nodes.)_")
        lines.append("")
    return lines


def _execution_plan(task: str) -> list[str]:
    """Stub: 3 placeholder steps acknowledging the user's task."""
    return [
        f"1. **Confirm scope** — review the Structured Context above and confirm it captures the task: \"{task[:80]}{'…' if len(task) > 80 else ''}\".",
        "2. **Identify first concrete action** — based on the validated context, what's the smallest next step that moves the work forward?",
        "3. **Schedule it** — pick a time-bounded slot (today / this week) for the first action; commit to a check-in afterwards.",
        "",
        "_Day 4 will replace these placeholder steps with task-type-aware execution derived from "
        "the GOAL and CONSTRAINT nodes in the Intent Graph._",
    ]


def main() -> None:
    state = require_active()

    task = state.get("task", "(unknown task)")
    turn_count = int(state.get("turn_count", 0))
    score = int(state.get("score_pct", 0))
    nodes = state.get("nodes", [])

    lines: list[str] = []
    lines.append("# Fathom Compiled Plan")
    lines.append("")
    lines.append(f"> Compiled from {turn_count} turn{'s' if turn_count != 1 else ''} of dialogue · Final Fathom Score: {score}%")
    lines.append("")
    lines.append("## 1. Intent Summary")
    lines.append("")
    lines.append(_intent_summary(task, turn_count))
    lines.append("")
    lines.append("## 2. Structured Context")
    lines.append("")
    lines.extend(_structured_context(nodes))
    lines.append("## 3. Validated Relationships")
    lines.append("")
    lines.append(
        "No causal relationships were explicitly confirmed in this session. "
        "_(Day 4 will add Causal Fathom Protocol — only edges where the user used explicit "
        "causal language ('because', 'so that', 'leads to') get rendered here.)_"
    )
    lines.append("")
    lines.append("## 4. Execution Plan")
    lines.append("")
    lines.extend(_execution_plan(task))
    lines.append("")
    lines.append("## 5. Approval Required")
    lines.append("")
    lines.append("> **Reply 'approve' to proceed with this plan, or describe what to change.**")
    lines.append("> If you approve, I'll begin execution. If you want to refine any section, say which and how.")
    lines.append("")

    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()
